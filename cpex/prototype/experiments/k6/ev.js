import http from 'k6/http';
import { SharedArray } from 'k6/data';
import { sleep, check } from 'k6';

const items = new SharedArray('items', function () {
  const content = JSON.parse(open('../../../../conf/loads.json'));
  return content;
});

export default function () {
    const i = Math.floor(Math.random() * items.length);
    const host = __ENV.HOST || 'evaluator';
    const url = `http://${host}/evaluate`;
    const body = JSON.stringify(items[i].cpex.oprf);
    const params = { headers: {'Content-Type': 'application/json'} };
    const res = http.post(url, body, params);
    // console.log(res.json());
    sleep(Math.random());
}