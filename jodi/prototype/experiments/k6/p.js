import http from 'k6/http';
import { SharedArray } from 'k6/data';
import { sleep, check } from 'k6';

const items = new SharedArray('items', function () {
  const content = JSON.parse(open('../../../../conf/loads.json'));
  return content;
});

export default function () {
    const i = Math.floor(Math.random() * items.length);
    const host = __ENV.HOST || 'provider-iwf';
    const params = { headers: {'Content-Type': 'application/json'} };

    const callDetails = {
        src: items[i].orig, 
        dst: items[i].dest
    };

    if (Math.random() < 0.5) {
        const res = http.post(`http://${host}/publish`, JSON.stringify({
            passport: items[i].passport,
            ...callDetails
        }), params);
        // console.log(res.body);
    } else {
        const res = http.get(`http://${host}/retrieve/${callDetails.src}/${callDetails.dst}`, params);
        // console.log(res.body);
    }
    
    sleep(Math.random());
}