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
    const cidGenReqs = {}

    for (const ev of record.jodi.evs) {
        cidGenReqs[ev] = {
            method: 'POST',
            url: `${ev}/evaluate`,
            body: JSON.stringify({
                ...record.jodi.oprf,
                bt: record.jodi.bt,
                peers: record.jodi.evs_peers,
            }),
            params: { 
                ...globalParams, 
                headers,
                tags: { name: 'CidGenerationProtocol' },
            }
        };
    }
    
    const responses = http.batch(cidGenReqs);
    const result = {};
    Object.keys(responses).map(key => {
        result[key] = [200, 201].includes(responses[key].status);
    })
    return result
}

const PublishProtocol = (record) => {
    // Generate CID for publishing
    const cidRess = CidGenerationProtocol(record);

    // Publish the record
    const pubReqs = []
    for (const ms of record.jodi.mss) {
        pubReqs.push({
            method: 'POST',
            url: `${ms}/publish`,
            body: JSON.stringify({
                idx: record.jodi.idx, 
                ctx: record.jodi.ctx, 
                sig: record.jodi.pub_sig,
                bt: record.jodi.bt,
                peers: record.jodi.mss_peers,
            }),
            params: { 
                ...globalParams, 
                headers,
                tags: { name: 'PublishProtocol' }
            }
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
    
    const retReqs = []
    for (const ms of record.jodi.mss) {
        retReqs.push({
            method: 'POST',
            url: `${ms}/retrieve`,
            body: JSON.stringify({
                idx: record.jodi.idx, 
                sig: record.jodi.ret_sig,
                bt: record.jodi.bt,
                peers: record.jodi.mss_peers,
            }),
            params: { 
                ...globalParams, 
                headers,
                tags: { name: 'RetrieveProtocol' }
            }
        });
    }

    const responses = http.batch(retReqs);

    return {
        cidRess,
        success: responses.some(res => res.status === 200)
    }
}

export function setup() {
    console.log(`VUs: ${numVUs}, Items: ${items.length}`);
};

export default function () {
    const i = ((__VU - 1) + __ITER * numVUs) % items.length;

    const pres = PublishProtocol(items[i]);
    const rres = RetrieveProtocol(items[i]);

    if (pres.success && rres.success) {
        let matched = true;
        for (const ev of Object.keys(pres.cidRess)) {
            if (pres.cidRess[ev] !== rres.cidRess[ev]) {
                matched = false;
                break;
            }
        }

        if (matched) {
            successfulCallsCounter.add(1);
        }
    }
    
    sleep(0.15);
}