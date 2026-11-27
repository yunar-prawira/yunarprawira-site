"""Reproducible local Chrome/CDP checks. No dependencies added to project."""
import asyncio
import base64
import json
import subprocess
import urllib.request
from pathlib import Path
import websockets

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / 'audit'

async def main():
    tabs = json.load(urllib.request.urlopen('http://127.0.0.1:9227/json'))
    async with websockets.connect(tabs[0]['webSocketDebuggerUrl'], max_size=32*1024*1024) as ws:
        seq = 0
        async def call(method, **params):
            nonlocal seq
            seq += 1
            await ws.send(json.dumps({'id': seq, 'method': method, 'params': params}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get('id') == seq:
                    if 'error' in msg:
                        raise RuntimeError(msg['error'])
                    return msg.get('result', {})
        async def js(expression):
            result = await call('Runtime.evaluate', expression=expression, returnByValue=True, awaitPromise=True)
            if 'exceptionDetails' in result:
                raise RuntimeError(result['exceptionDetails'])
            return result['result'].get('value')
        async def navigate():
            await call('Page.navigate', url='http://127.0.0.1:8765/docs/')
            await asyncio.sleep(.6)
            await js('document.fonts.ready.then(()=>true)')
        async def viewport(w,h):
            await call('Emulation.setDeviceMetricsOverride',width=w,height=h,deviceScaleFactor=1,mobile=False)
        measure = (AUDIT/'rupa-home-measure.js').read_text()
        await viewport(1440,900)
        await navigate()
        await js("localStorage.clear();location.reload()")
        await asyncio.sleep(.5)
        layout = {}
        for lang in ['id','en']:
            await js(f'document.querySelector("[data-language={lang}]").click()')
            for w,h in [(1440,900),(1280,900),(390,844)]:
                await viewport(w,h)
                metrics = await js(measure)
                layout[f'{lang}-{w}'] = metrics
                assert metrics['scroll'] == metrics['client'], metrics
                assert len(metrics['edges']) <= 4, metrics['edges']
                assert not [b for b in metrics['blocks'] if b['selector']=='P' and b['characters']<=120 and b['lines']>1 and w>=1280]
                if lang=='id' and w!=1280:
                    shot = await call('Page.captureScreenshot',format='png',captureBeyondViewport=True,clip={'x':0,'y':0,'width':w,'height':metrics['height'],'scale':1})
                    (AUDIT/f'rupa-home-{w}.png').write_bytes(base64.b64decode(shot['data']))
        (AUDIT/'rupa-home-layout.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2))
        state_expr = '''({lang:document.documentElement.lang,title:document.title,description:document.querySelector('meta[name=description]').content,blocks:[...document.querySelectorAll('.role,.lede,.contact h2')].map(e=>e.textContent),pressed:[...document.querySelectorAll('[data-language]')].map(e=>[e.textContent,e.getAttribute('aria-pressed')])})'''
        states = {}
        for lang in ['en','id']:
            await js(f'document.querySelector("[data-language={lang}]").click()')
            states['click-'+lang] = await js(state_expr)
            await call('Page.reload',ignoreCache=True)
            await asyncio.sleep(.5)
            states['refresh-'+lang] = await js(state_expr)
            assert states['click-'+lang] == states['refresh-'+lang]
        # Keyboard Tab/Enter operates the actual focused language control.
        await js('document.querySelector("[data-language=id]").focus()')
        await call('Input.dispatchKeyEvent',type='keyDown',key='Tab',code='Tab',windowsVirtualKeyCode=9)
        await call('Input.dispatchKeyEvent',type='keyUp',key='Tab',code='Tab',windowsVirtualKeyCode=9)
        assert await js('document.activeElement.dataset.language') == 'en'
        await call('Input.dispatchKeyEvent',type='keyDown',key='Enter',code='Enter',windowsVirtualKeyCode=13,text='\r')
        await call('Input.dispatchKeyEvent',type='keyUp',key='Enter',code='Enter',windowsVirtualKeyCode=13)
        states['keyboard-EN'] = await js(state_expr)
        assert states['keyboard-EN']['lang']=='en'
        states['targets'] = await js('([...document.querySelectorAll("[data-language]")].map(e=>({text:e.textContent,width:e.offsetWidth,height:e.offsetHeight})))')
        (AUDIT/'rupa-home-toggle.json').write_text(json.dumps(states,ensure_ascii=False,indent=2))
        await call('Emulation.setScriptExecutionDisabled',value=True)
        await navigate()
        nojs = await js('({lang:document.documentElement.lang,toggleHidden:document.querySelector(".languages").hidden,lede:document.querySelector(".lede").textContent})')
        assert nojs['lang']=='id' and nojs['toggleHidden']
        (AUDIT/'rupa-home-nojs.json').write_text(json.dumps(nojs,ensure_ascii=False,indent=2))
        await call('Emulation.setScriptExecutionDisabled',value=False)
        old = subprocess.check_output(['git','show','HEAD:docs/index.html'],cwd=ROOT,text=True)
        frame = (await call('Page.getFrameTree'))['frameTree']['frame']['id']
        await call('Page.setDocumentContent',frameId=frame,html=old)
        before = {}
        for w,h in [(1440,900),(390,844)]:
            await viewport(w,h)
            before[str(w)] = await js('({height:document.documentElement.scrollHeight,scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth})')
        (AUDIT/'rupa-home-before-height.json').write_text(json.dumps(before,indent=2))
        print(json.dumps({'layouts':{k:{'height':v['height'],'edges':v['edges'],'scroll':v['scroll'],'client':v['client'],'multiline':[b for b in v['blocks'] if b['lines']>1]} for k,v in layout.items()},'toggle':states,'nojs':nojs,'before':before},ensure_ascii=False,indent=2))

asyncio.run(main())
