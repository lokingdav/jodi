import http from 'k6/http';
import { SharedArray } from 'k6/data';
import { sleep, check } from 'k6';

const items = new SharedArray('items', function () {
  const content = JSON.parse(open('../../../../conf/loads.json'));
  return content;
});

export default function () {
    const i = Math.floor(Math.random() * items.length);
    const host = __ENV.HOST || 'message-store';
    const params = { headers: {'Content-Type': 'application/json'} };

    if (Math.random() < 0.5) {
        const res = http.post(`http://${host}/publish`, JSON.stringify({
            idx: items[i].cpex.idx, 
            ctx: items[i].cpex.ctx, 
            sig: items[i].cpex.pub_sig
        }), params);
        // console.log(res.body);
    } else {
        const res = http.post(`http://${host}/retrieve`, JSON.stringify({
            idx: items[i].cpex.idx, 
            sig: items[i].cpex.ret_sig
        }), params);
        // console.log(res.body);
    }
    
    sleep(Math.random());
}