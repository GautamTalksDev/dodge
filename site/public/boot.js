// Runs before first paint: mark JS on, so reveal styles only apply when they can finish.
document.documentElement.classList.add("js");
// Film grain: one 256px noise tile, made once, used as a fixed overlay.
addEventListener("DOMContentLoaded", function () {
  try {
    var c = document.createElement("canvas"); c.width = c.height = 256;
    var x = c.getContext("2d"), img = x.createImageData(256, 256), d = img.data;
    for (var i = 0; i < d.length; i += 4) { var v = (Math.random() * 255) | 0; d[i] = d[i + 1] = d[i + 2] = v; d[i + 3] = 255; }
    x.putImageData(img, 0, 0);
    document.documentElement.style.setProperty("--grain", "url(" + c.toDataURL("image/png") + ")");
  } catch (e) { /* no grain is fine */ }
});
