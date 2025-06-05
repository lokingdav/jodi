import http from 'k6/http';
import { SharedArray } from 'k6/data';
import { sleep, check } from 'k6';
import { Trend } from 'k6/metrics';

const items = new SharedArray('items', function () {
  const content = JSON.parse(open('../../../../conf/loads.json'));
  return content;
});

let reqSize = new Trend('cidgen_req_size');
let resSize = new Trend('cidgen_res_size');

export default function () {
    const record = items[Math.floor(Math.random() * items.length)];
    const host = __ENV.HOST || 'evaluator';
    const url = `http://${host}/evaluate`;
    const body = JSON.stringify({
        ...record.jodi.oprf,
        bt: record.jodi.bt,
        peers: record.jodi.evs_peers,
    });
    const params = { headers: {'Content-Type': 'application/json'} };
    const res = http.post(url, body, params);
    
    reqSize.add(res.request.body.length);
    resSize.add(res.body.length);

    sleep(Math.random());
}