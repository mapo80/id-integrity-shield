DEFAULT_WEIGHTS = {
    "trufor": 0.35,
    "noiseprintpp": 0.25,
    "deep_onnx": 0.20,
    "splicing": 0.10,
    "noise_inconsistency": 0.10,
    "jpeg_blockiness": 0.05,
    "ela95": 0.05,
    "jpeg_ghosts": 0.05,
    "copy_move": 0.00,
    "exif": 0.05
}
def fuse_scores(per_check, weights):
    total = 0.0; wsum = 0.0
    for k,v in per_check.items():
        w = weights.get(k, 0.0)
        s = v.get("score")
        if s is None: 
            continue
        total += w * float(s)
        wsum += w
    return total / (wsum if wsum>0 else 1.0)