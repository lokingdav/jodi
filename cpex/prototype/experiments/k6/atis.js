import http from 'k6/http';
import { SharedArray } from 'k6/data';
import { sleep, check } from 'k6';
import { Counter } from 'k6/metrics';

const items = new SharedArray('items', function () {
  const content = JSON.parse(open('../../../../conf/loads.json'));
  return content;
});

const numVUs = parseInt(__ENV.VUS, 10);

if (isNaN(numVUs)) {
    throw new Error('VUS must be a number');
}

const successfulCallsCounter = new Counter('successful_calls');
const commonHeaders = { 'Content-Type': 'application/json' };
const globalParams = {};

if (__ENV.TIMEOUT) {
    globalParams.timeout = __ENV.TIMEOUT;
}

const PublishProtocol = (record) => {
    const headers = {
        ...commonHeaders,
        'Authorization': `Bearer ${record.atis.pub_bearer}`
    };

    const res = http.post(record.atis.pub_url, JSON.stringify({ passports: [record.passport] }), { ...globalParams, headers });

    return res.status === 200;
}

const RetrieveProtocol = (record) => {
    const headers = {
        ...commonHeaders,
        'Authorization': `Bearer ${record.atis.ret_bearer}`
    };

    const res = http.get(record.atis.ret_url, { ...globalParams, headers });

    return res.status === 200;
}

export function setup() {
    console.log(`VUs: ${numVUs}, Items: ${items.length}`);
};

export default function () {
    const i = ((__VU - 1) + __ITER * numVUs) % items.length;
    
    const isPublished = PublishProtocol(items[i]);
    const isRetrieved = RetrieveProtocol(items[i]);

    if (isPublished && isRetrieved) {
        successfulCallsCounter.add(1);
    }

    sleep(0.15);
}