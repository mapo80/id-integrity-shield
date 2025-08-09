from PIL import Image, ImageOps
import numpy as np

def save_heatmap_gray(hm01, out_path):
    arr = np.clip(np.asarray(hm01)*255.0, 0, 255).astype('uint8')
    Image.fromarray(arr).save(out_path)

def fuse_heatmaps(maps, weights=None):
    if not maps: return None
    # determine target size as max H,W among maps
    sizes = [(np.asarray(hm).shape[0], np.asarray(hm).shape[1]) for hm in maps.values()]
    Ht = max(h for h,_ in sizes); Wt = max(w for _,w in sizes)
    acc = None; ws = 0.0
    from PIL import Image
    for name, hm in maps.items():
        a = np.asarray(hm, dtype=float)
        if a.shape != (Ht, Wt):
            a = np.array(Image.fromarray((a*255).astype('uint8')).resize((Wt,Ht), Image.BILINEAR), dtype=float)/255.0
        w = 1.0 if weights is None else float(weights.get(name,1.0))
        acc = a*w if acc is None else acc + a*w
        ws += w
    fused = acc / (ws if ws>0 else 1.0)
    fused = (fused - fused.min())/(fused.max()-fused.min()+1e-8)
    return fused

def overlay_on_image(pil_img, hm01, alpha=0.5):
    base = pil_img.convert("RGBA")
    h, w = hm01.shape
    hm_rgb = (np.stack([hm01*255]*3, axis=-1)).astype('uint8')
    hm_img = Image.fromarray(hm_rgb).resize(base.size, Image.BILINEAR).convert("L")
    heat = ImageOps.colorize(hm_img, black="#00000000", white="#FF0000").convert("RGBA")
    heat.putalpha(int(alpha*255))
    return Image.alpha_composite(base, heat)