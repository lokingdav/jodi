import http from 'k6/http';
import { SharedArray } from 'k6/data';
import { sleep, check } from 'k6';

const items = new SharedArray('items', function () {
  const content = JSON.parse(open('../../../../conf/loads.json'));
  return content;
});

export default function () {
    const i = Math.floor(Math.random() * items.length);

    const headers = {'Content-Type': 'application/json'};

    const cidGenReqs = []
    for (const ev of items[i].cpex.evs) {
        cidGenReqs.push({
            method: 'POST',
            url: `${ev}/evaluate`,
            body: JSON.stringify(items[i].cpex.oprf),
            params: { headers }
        });
    }
    
    const cidsres = http.batch(cidGenReqs);

    const pubReqs = []
    const retReqs = []
    
    for (const ms of items[i].cpex.mss) {
        pubReqs.push({
            method: 'POST',
            url: `${ms}/publish`,
            body: JSON.stringify({
                idx: items[i].cpex.idx, 
                ctx: items[i].cpex.ctx, 
                sig: items[i].cpex.pub_sig
            }),
            params: { headers }
        });

        retReqs.push({
            method: 'POST',
            url: `${ms}/retrieve`,
            body: JSON.stringify({
                idx: items[i].cpex.idx, 
                sig: items[i].cpex.ret_sig
            }),
            params: { headers }
        });
    }

    const pubres = http.batch(pubReqs);

    const retres = http.batch(retReqs);
    sleep(1);
}