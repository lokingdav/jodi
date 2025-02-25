import http from 'k6/http';
import { SharedArray } from 'k6/data';
import { sleep, check } from 'k6';

const items = new SharedArray('items', function () {
  const content = JSON.parse(open('../../../../conf/loads.json'));
  return content;
});

const commonHeaders = { 'Content-Type': 'application/json' };

const PublishProtocol = (record) => {
    const headers = {
        ...commonHeaders,
        'Authorization': `Bearer ${record.atis.pub_bearer}`
    };

    return http.post(record.atis.pub_url, JSON.stringify({ passports: [record.passport] }), { headers });
}

const RetrieveProtocol = (record) => {
    const headers = {
        ...commonHeaders,
        'Authorization': `Bearer ${record.atis.ret_bearer}`
    };

    return http.get(record.atis.ret_url, { headers });
}

export default function () {
    const i = Math.floor(Math.random() * items.length);
    
    PublishProtocol(items[i]);
    RetrieveProtocol(items[i]);

    sleep(0.15);
}