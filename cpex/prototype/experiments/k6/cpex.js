import http from 'k6/http';
import { SharedArray } from 'k6/data';
import { sleep, check } from 'k6';

const items = new SharedArray('items', function () {
  const content = JSON.parse(open('../../../../conf/loads.json'));
  return content;
});

const headers = { 'Content-Type': 'application/json' };

const CidGenerationProtocol = (record) => {
    const cidGenReqs = []

    for (const ev of record.cpex.evs) {
        cidGenReqs.push({
            method: 'POST',
            url: `${ev}/evaluate`,
            body: JSON.stringify(record.cpex.oprf),
            params: { headers }
        });
    }
    
    return http.batch(cidGenReqs);
}

const PublishProtocol = (record) => {
    // Generate CID for the record
    CidGenerationProtocol(record);

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
            params: { headers }
        });
    }

    return http.batch(pubReqs);
}

const RetrieveProtocol = (record) => {
    // Generate CID for the record
    CidGenerationProtocol(record);

    const retReqs = []
    for (const ms of record.cpex.mss) {
        retReqs.push({
            method: 'POST',
            url: `${ms}/retrieve`,
            body: JSON.stringify({
                idx: record.cpex.idx, 
                sig: record.cpex.ret_sig
            }),
            params: { headers }
        });
    }

    return http.batch(retReqs);
}

export default function () {
    const i = Math.floor(Math.random() * items.length);

    PublishProtocol(items[i]);
    RetrieveProtocol(items[i]);
    
    sleep(0.15);
}