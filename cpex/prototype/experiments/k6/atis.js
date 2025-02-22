import http from 'k6/http';
import { SharedArray } from 'k6/data';
import { sleep, check } from 'k6';

const items = new SharedArray('items', function () {
  const content = JSON.parse(open('../../../../conf/loads.json'));
  return content;
});

export default function () {
    const i = Math.floor(Math.random() * items.length);

    const pubHeaders = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${items[i].atis.pub_bearer}`
    };

    http.post(items[i].atis.pub_url, JSON.stringify({ passports: [items[i].passport] }), { headers: pubHeaders });

    const retHeaders = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${items[i].atis.ret_bearer}`
    }
    const res = http.get(items[i].atis.ret_url, { headers: retHeaders });
    
    sleep(1);
}