import {readdirSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
for(const f of readdirSync('web').filter(x=>x.endsWith('.js'))){const r=spawnSync(process.execPath,['--check','web/'+f],{stdio:'inherit'});if(r.status)process.exit(r.status);}
console.log('JavaScript syntax checks passed.');
