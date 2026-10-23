import fs from 'node:fs/promises';
import path from 'node:path';
import {bundle} from '@remotion/bundler';
import {selectComposition, renderMedia, renderStill} from '@remotion/renderer';

const data=JSON.parse(await fs.readFile('data.json','utf8'));
if(data.demo && !process.argv.includes('--allow-demo')) throw new Error('Synthetic sample: replace data or explicitly use --allow-demo for testing.');
const out=path.resolve('out');
await fs.mkdir(out,{recursive:true});
const serveUrl=await bundle({entryPoint:path.resolve('src/index.tsx')});
const inputProps={data};
const browserExecutable=process.env.LIVECANVAS_BROWSER || process.env.LIVECHART_BROWSER || undefined;
const chromiumOptions={gl:'swangle'};
const chromeMode='headless-shell';
const composition=await selectComposition({serveUrl,id:'LiveCanvas',inputProps,browserExecutable,chromiumOptions,chromeMode});
const coverFrame=78;
const common={composition,serveUrl,inputProps,browserExecutable,chromiumOptions,chromeMode};
console.log('Rendering PNG frames sequentially using software graphics.');
await renderMedia({...common,codec:'h264',pixelFormat:'yuv420p',colorSpace:'bt709',imageFormat:'png',crf:16,outputLocation:path.join(out,'motion.mp4'),concurrency:1,disallowParallelEncoding:true});
await renderStill({...common,frame:coverFrame,imageFormat:'jpeg',jpegQuality:100,output:path.join(out,'cover.jpg')});
for(const frame of [0,30,60,78]) await renderStill({...common,frame,imageFormat:'png',output:path.join(out,`frame-${frame}.png`)});
for(const name of ['motion.mp4','cover.jpg','frame-0.png','frame-30.png','frame-60.png','frame-78.png']) {
  const stat=await fs.stat(path.join(out,name));
  if(stat.size===0) throw new Error(`Empty render: ${name}`);
}
await fs.writeFile(path.join(out,'render.json'),JSON.stringify({fps:composition.fps,durationInFrames:composition.durationInFrames,width:composition.width,height:composition.height,coverFrame,coverTime:coverFrame/composition.fps,demo:data.demo,rendering:{browser:browserExecutable||'Remotion-managed Chrome Headless Shell',chromeMode,gl:'swangle',imageFormat:'png',concurrency:1,parallelEncoding:false,colorSpace:'bt709'}},null,2));
console.log(`Rendered ${out}; coverTime=${coverFrame/composition.fps}s. Live Photo pairing is a separate step.`);
