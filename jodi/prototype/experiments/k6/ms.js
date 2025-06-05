import http from 'k6/http';
import { SharedArray } from 'k6/data';
import { sleep, check } from 'k6';
import { Trend } from 'k6/metrics';

const items = new SharedArray('items', function () {
  const content = JSON.parse(open('../../../../conf/loads.json'));
  return content;
});

let pubReqSize = new Trend('pub_req_size');
let pubResSize = new Trend('pub_res_size');

let retReqSize = new Trend('ret_req_size');
let retResSize = new Trend('ret_res_size');

export default function () {
    const record = items[Math.floor(Math.random() * items.length)];
    const host = __ENV.HOST || 'message-store';
    const params = { headers: {'Content-Type': 'application/json'} };

    if (Math.random() < 0.5) {
        const res = http.post(`http://${host}/publish`, JSON.stringify({
            idx: record.jodi.idx, 
            ctx: record.jodi.ctx, 
            sig: record.jodi.pub_sig,
            bt: record.jodi.bt,
            peers: record.jodi.mss_peers,
        }), params);
        pubReqSize.add(res.request.body.length);
        pubResSize.add(res.body.length);
    } else {
        const res = http.post(`http://${host}/retrieve`, JSON.stringify({
            idx: record.jodi.idx, 
            sig: record.jodi.ret_sig,
            bt: record.jodi.bt,
            peers: record.jodi.mss_peers,
        }), params);
        retReqSize.add(res.request.body.length);
        retResSize.add(res.body.length);
    }
    
    sleep(0.15);
}