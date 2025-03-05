import http from 'k6/http';
import { sleep } from 'k6';
import { SharedArray } from 'k6/data';
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
const headers = { 'Content-Type': 'application/json' };
const globalParams = {};

if (__ENV.TIMEOUT) {
    globalParams.timeout = __ENV.TIMEOUT;
}

const CidGenerationProtocol = (record) => {
    const cidGenReqs = []

    for (const ev of record.cpex.evs) {
        cidGenReqs.push({
            method: 'POST',
            url: `${ev}/evaluate`,
            body: JSON.stringify(record.cpex.oprf),
            params: { ...globalParams, headers }
        });
    }
    
    const responses = http.batch(cidGenReqs);

    return responses.map(res => res.status === 200)
}

const PublishProtocol = (record) => {
    // Generate CID for publishing
    const cidRess = CidGenerationProtocol(record);

    // Publish the record
    const pubReqs = []
    for (const ms of record.cpex.mss) {
        pubReqs.push({
            method: 'POST',
            url: `${ms}/publish`,
            body: JSON.stringify({
                idx: record.cpex.idx, 
                ctx: record.cpex.ctx, 
                sig: record.cpex.pub_sig
            }),
            params: { ...globalParams, headers }
        });
    }

    const responses = http.batch(pubReqs);

    return {
        cidRess,
        success: responses.some(res => res.status === 200) // only 1 success is enough (replication factor)
    }
}

const RetrieveProtocol = (record) => {
    // Generate CID for retrieving
    const cidRess = CidGenerationProtocol(record);
    
    // usually, only one request is okay. We may use Promise.race()
    const ms = record.cpex.mss[Math.floor(Math.random() * record.cpex.mss.length)];
    const res = http.post(`${ms}/retrieve`, JSON.stringify({
        idx: record.cpex.idx, 
        sig: record.cpex.ret_sig
    }), { ...globalParams, headers });

    return {
        cidRess,
        success: res.status === 200 
    }
}

export function setup() {
    console.log(`VUs: ${numVUs}, Items: ${items.length}`);
};

export default function () {
    const i = ((__VU - 1) + __ITER * numVUs) % items.length;

    const pres = PublishProtocol(items[i]);
    const rres = RetrieveProtocol(items[i]);

    if (pres.success && rres.success && pres.cidRess.length === rres.cidRess.length) {
        if (pres.cidRess.every((val, index) => val === rres.cidRess[index])) { 
            // call ids are same during publish and retrieve so it is a successful call
            successfulCallsCounter.add(1);
        }
    }
    
    sleep(0.15);
}