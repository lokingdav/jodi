import http from 'k6/http';
import { SharedArray } from 'k6/data';
import { sleep, check } from 'k6';
import { Counter } from 'k6/metrics';

const items = new SharedArray('items', function () {
  const content = JSON.parse(open('../../../../conf/loads.json'));
  return content;
});

const successfulCallsCounter = new Counter('successful_calls');

const commonHeaders = { 'Content-Type': 'application/json' };

const PublishProtocol = (record) => {
    const headers = {
        ...commonHeaders,
        'Authorization': `Bearer ${record.atis.pub_bearer}`
    };

    const res = http.post(record.atis.pub_url, JSON.stringify({ passports: [record.passport] }), { headers });

    return res.status === 200;
}

const RetrieveProtocol = (record) => {
    const headers = {
        ...commonHeaders,
        'Authorization': `Bearer ${record.atis.ret_bearer}`
    };

    const res = http.get(record.atis.ret_url, { headers });

    return res.status === 200;
}

export default function () {
    const i = Math.floor(Math.random() * items.length);
    
    const isPublished = PublishProtocol(items[i]);
    const isRetrieved = RetrieveProtocol(items[i]);

    if (isPublished && isRetrieved) {
        successfulCallsCounter.add(1);
    }

    sleep(0.15);
}