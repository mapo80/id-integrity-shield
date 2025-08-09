
def main():
    from fastapi.testclient import TestClient
    from app.main import app
    from PIL import Image, ImageDraw
    from pathlib import Path
    import io

    client = TestClient(app)
    # health
    r = client.get('/v1/health')
    assert r.status_code == 200

    # analyze
    im = Image.new('RGB', (256,160), 'white'); dr = ImageDraw.Draw(im); dr.rectangle([60,40,196,120], outline='black', width=4)
    bio = io.BytesIO(); im.save(bio, format='PNG'); bio.seek(0)
    files = {'file': ('doc.png', bio.getvalue(), 'image/png')}
    data = {'profile':'recapture-id','save_artifacts':True}
    # no API key set in env => auth disabled for tests
    r = client.post('/v1/analyze', files=files, data=data)
    assert r.status_code == 200, r.text
    js = r.json()
    assert 'tamper_score' in js and 'per_check' in js and 'confidence' in js
    return True

if __name__=='__main__':
    print(main())
