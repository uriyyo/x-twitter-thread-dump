//! Python bindings for rendering static HTML to RGBA pixels with Blitz.
//!
//! The renderer is intentionally offline: only `data:` URLs are resolved, every other
//! sub-resource fails immediately (same as Chrome with `offline=True`).

use std::sync::{Arc, LazyLock, Mutex};

use anyrender::render_to_buffer;
use anyrender_skia::SkiaImageRenderer;
use anyrender_vello_cpu::VelloCpuImageRenderer;
use blitz_dom::{BaseDocument, DocumentConfig, FontContext, NodeId};
use blitz_html::HtmlDocument;
use blitz_paint::paint_scene;
use blitz_traits::net::{Bytes, NetHandler, NetProvider, Request};
use blitz_traits::shell::{ColorScheme, Viewport};
use data_url::DataUrl;
use parley::fontique::{Collection, CollectionOptions, SourceCache};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyBytes;

/// System font discovery is slow, so do it once and share the collection between renders.
static FONT_CTX: LazyLock<Mutex<FontContext>> = LazyLock::new(|| {
    Mutex::new(FontContext {
        collection: Collection::new(CollectionOptions {
            shared: true,
            system_fonts: true,
        }),
        source_cache: SourceCache::new_shared(),
    })
});

/// Number of `resolve` passes: images/css-urls are fetched during a pass and ingested on the next one.
const RESOLVE_PASSES: usize = 3;

struct DataUrlProvider;

impl NetProvider for DataUrlProvider {
    fn fetch(&self, _doc_id: usize, request: Request, handler: Box<dyn NetHandler>) {
        let url = request.url.to_string();

        // Empty body makes the handler report a decode error, so the resource stops being pending.
        let body = match request.url.scheme() {
            "data" => DataUrl::process(&url)
                .ok()
                .and_then(|data_url| data_url.decode_to_vec().ok())
                .map(|(body, _)| Bytes::from(body))
                .unwrap_or_default(),
            _ => Bytes::new(),
        };

        handler.bytes(url, body);
    }
}

#[derive(Clone, Copy, Debug)]
struct BoxRect {
    x: f64,
    y: f64,
    width: f64,
    height: f64,
}

/// Element bounding box in CSS pixels, relative to the captured element.
#[pyclass(frozen, skip_from_py_object, module = "blitz_render")]
#[derive(Clone)]
struct Rect {
    #[pyo3(get)]
    x: f64,
    #[pyo3(get)]
    y: f64,
    #[pyo3(get)]
    width: f64,
    #[pyo3(get)]
    height: f64,
}

#[pymethods]
impl Rect {
    #[getter]
    fn left(&self) -> f64 {
        self.x
    }

    #[getter]
    fn top(&self) -> f64 {
        self.y
    }

    #[getter]
    fn right(&self) -> f64 {
        self.x + self.width
    }

    #[getter]
    fn bottom(&self) -> f64 {
        self.y + self.height
    }

    fn __repr__(&self) -> String {
        format!(
            "Rect(x={}, y={}, width={}, height={})",
            self.x, self.y, self.width, self.height
        )
    }
}

/// Rendered image as raw RGBA8 pixels (not premultiplied), plus the requested element rects.
#[pyclass(frozen, module = "blitz_render")]
struct RenderResult {
    #[pyo3(get)]
    width: u32,
    #[pyo3(get)]
    height: u32,
    #[pyo3(get)]
    scale: f64,
    #[pyo3(get)]
    rects: Vec<Rect>,
    rgba: Vec<u8>,
}

#[pymethods]
impl RenderResult {
    /// Raw RGBA8 pixels, row-major, `width * height * 4` bytes.
    #[getter]
    fn rgba<'py>(&self, py: Python<'py>) -> Bound<'py, PyBytes> {
        PyBytes::new(py, &self.rgba)
    }

    /// Encode pixels as PNG.
    #[pyo3(signature = (*, fast = true))]
    fn png<'py>(&self, py: Python<'py>, fast: bool) -> PyResult<Bound<'py, PyBytes>> {
        let encoded = py
            .detach(|| encode_png(&self.rgba, self.width, self.height, fast))
            .map_err(|err| PyRuntimeError::new_err(err.to_string()))?;

        Ok(PyBytes::new(py, &encoded))
    }

    fn __repr__(&self) -> String {
        format!(
            "RenderResult(width={}, height={}, scale={}, rects={})",
            self.width,
            self.height,
            self.scale,
            self.rects.len()
        )
    }
}

fn encode_png(rgba: &[u8], width: u32, height: u32, fast: bool) -> Result<Vec<u8>, png::EncodingError> {
    let mut out = Vec::new();

    let mut encoder = png::Encoder::new(&mut out, width, height);
    encoder.set_color(png::ColorType::Rgba);
    encoder.set_depth(png::BitDepth::Eight);
    encoder.set_compression(if fast {
        png::Compression::Fast
    } else {
        png::Compression::Balanced
    });

    let mut writer = encoder.write_header()?;
    writer.write_image_data(rgba)?;
    writer.finish()?;

    Ok(out)
}

#[derive(Clone, Copy)]
enum Backend {
    VelloCpu,
    Skia,
}

struct RenderOptions {
    backend: Backend,
    width: u32,
    height: u32,
    scale: f64,
    color_scheme: ColorScheme,
    selector: Option<String>,
    rects_selector: Option<String>,
}

fn bounding_rect(doc: &BaseDocument, node_id: NodeId) -> Option<BoxRect> {
    doc.get_client_bounding_rect(node_id).map(|rect| BoxRect {
        x: rect.x,
        y: rect.y,
        width: rect.width,
        height: rect.height,
    })
}

fn query_one(doc: &BaseDocument, selector: &str) -> Result<NodeId, String> {
    doc.query_selector(selector)
        .map_err(|err| format!("Invalid selector {selector:?}: {err:?}"))?
        .ok_or_else(|| format!("No element matches selector {selector:?}"))
}

fn query_all(doc: &BaseDocument, selector: &str) -> Result<Vec<NodeId>, String> {
    doc.query_selector_all(selector)
        .map(|ids| ids.into_iter().collect())
        .map_err(|err| format!("Invalid selector {selector:?}: {err:?}"))
}

/// Copy a sub-rectangle out of an RGBA8 buffer.
fn crop(src: &[u8], src_width: u32, x: u32, y: u32, width: u32, height: u32) -> Vec<u8> {
    let row_len = width as usize * 4;
    let mut out = Vec::with_capacity(row_len * height as usize);

    for row in y..y + height {
        let start = (row as usize * src_width as usize + x as usize) * 4;
        out.extend_from_slice(&src[start..start + row_len]);
    }

    out
}

fn render_html(html: &str, opts: &RenderOptions) -> Result<RenderResult, String> {
    let scale = opts.scale;
    let font_ctx = FONT_CTX.lock().map_err(|err| err.to_string())?.clone();

    let mut document = HtmlDocument::from_html(
        html,
        DocumentConfig {
            viewport: Some(Viewport::new(
                (opts.width as f64 * scale) as u32,
                (opts.height as f64 * scale) as u32,
                scale as f32,
                opts.color_scheme,
            )),
            net_provider: Some(Arc::new(DataUrlProvider)),
            font_ctx: Some(font_ctx),
            ..Default::default()
        },
    );
    let doc: &mut BaseDocument = &mut document;

    for _ in 0..RESOLVE_PASSES {
        doc.resolve(0.0);
    }

    let root_id = doc.root_element().id;
    let target_id = match &opts.selector {
        Some(selector) => query_one(doc, selector)?,
        None => root_id,
    };
    let target = bounding_rect(doc, target_id).ok_or("Captured element has no layout box")?;

    let rects = match &opts.rects_selector {
        Some(selector) => query_all(doc, selector)?
            .into_iter()
            .filter_map(|id| bounding_rect(doc, id))
            .map(|rect| Rect {
                x: rect.x - target.x,
                y: rect.y - target.y,
                width: rect.width,
                height: rect.height,
            })
            .collect(),
        None => Vec::new(),
    };

    // Paint from the document origin down to the bottom of the target, then crop to the target.
    // (`paint_scene` only accepts non-negative offsets, so we can't translate the scene instead.)
    let page = bounding_rect(doc, root_id).ok_or("Document has no layout box")?;
    let page_width = (page.width.max(opts.width as f64) * scale).ceil() as u32;
    let page_height = ((target.y + target.height).max(1.0) * scale).ceil() as u32;

    let buffer = match opts.backend {
        Backend::VelloCpu => render_to_buffer::<VelloCpuImageRenderer, _>(
            |scene| paint_scene(scene, doc, scale, page_width, page_height, 0, 0),
            page_width,
            page_height,
        ),
        Backend::Skia => render_to_buffer::<SkiaImageRenderer, _>(
            |scene| paint_scene(scene, doc, scale, page_width, page_height, 0, 0),
            page_width,
            page_height,
        ),
    };

    let x = ((target.x * scale).floor().max(0.0) as u32).min(page_width);
    let y = ((target.y * scale).floor().max(0.0) as u32).min(page_height);
    let width = ((target.width * scale).ceil() as u32).min(page_width - x);
    let height = ((target.height * scale).ceil() as u32).min(page_height - y);

    let rgba = if (x, y, width, height) == (0, 0, page_width, page_height) {
        buffer
    } else {
        crop(&buffer, page_width, x, y, width, height)
    };

    Ok(RenderResult {
        width,
        height,
        scale,
        rects,
        rgba,
    })
}

/// Render HTML to an RGBA image.
///
/// `width`/`height` are the viewport size in CSS pixels; the image is as tall as the captured
/// element, regardless of `height`. `selector` picks the element to capture (whole document
/// by default); `rects_selector` collects bounding boxes of matching elements, relative to it.
/// The GIL is released while rendering, so calls can run in parallel from a thread pool.
#[pyfunction]
#[pyo3(signature = (
    html,
    /,
    *,
    width = 500,
    height = 1000,
    scale = 1.0,
    color_scheme = "light",
    selector = None,
    rects_selector = None,
    backend = "skia",
))]
#[allow(clippy::too_many_arguments)]
fn render(
    py: Python<'_>,
    html: String,
    width: u32,
    height: u32,
    scale: f64,
    color_scheme: &str,
    selector: Option<String>,
    rects_selector: Option<String>,
    backend: &str,
) -> PyResult<RenderResult> {
    if width == 0 || height == 0 {
        return Err(PyValueError::new_err("width and height must be positive"));
    }
    if !(scale.is_finite() && scale > 0.0) {
        return Err(PyValueError::new_err("scale must be a positive number"));
    }

    let color_scheme = match color_scheme {
        "light" => ColorScheme::Light,
        "dark" => ColorScheme::Dark,
        other => {
            return Err(PyValueError::new_err(format!(
                "color_scheme must be 'light' or 'dark', got {other:?}"
            )));
        }
    };

    let backend = match backend {
        "vello" => Backend::VelloCpu,
        "skia" => Backend::Skia,
        other => {
            return Err(PyValueError::new_err(format!(
                "backend must be 'vello' or 'skia', got {other:?}"
            )));
        }
    };

    let opts = RenderOptions {
        backend,
        width,
        height,
        scale,
        color_scheme,
        selector,
        rects_selector,
    };

    py.detach(|| render_html(&html, &opts))
        .map_err(PyValueError::new_err)
}

#[pymodule]
fn _blitz_render(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(render, m)?)?;
    m.add_class::<RenderResult>()?;
    m.add_class::<Rect>()?;
    Ok(())
}
