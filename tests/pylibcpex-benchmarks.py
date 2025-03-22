import time
from pylibcpex import Oprf, Voprf, Ciphering, Utils, KeyRotation

numIters = 1000

def startTimer():
    return time.perf_counter()

def endTimer(test_name, start, numIters):
    end_time = time.perf_counter()
    duration = end_time - start
    print("\n%s\nTotal: %d runs in %0.1f ms\nAvg: %f ms"
        % (test_name, numIters, duration * 1000, duration * 1000 / numIters))

def bench_oprf():
    callDetails = "+123456789|+1987654321|1733427398"
    (privk, publk) = Oprf.keygen()

    # Check for correctness first
    (x1, r1) = Oprf.blind(callDetails)
    (x2, r2) = Oprf.blind(callDetails)
    assert(x1 != x2) # blindings must differ
    assert(r1 != r2) # random scalars must differ
    (fx1, vk1) = Oprf.evaluate(privk, publk, x1)
    (fx2, vk2) = Oprf.evaluate(privk, publk, x2)
    assert(fx1 != fx2) # intermediate evaluations must differ
    assert(vk1 == vk2 == publk) # verification params must be public key of PRF key
    digest1 = Oprf.unblind(fx1, vk1, r1)
    digest2 = Oprf.unblind(fx2, vk2, r2)
    assert(digest1 == digest2) # Must final unblinded results must match

    start = startTimer()
    for i in range(numIters):
        (x, r) = Oprf.blind(callDetails)
    endTimer("Oprf::blind", start, numIters)

    start = startTimer()
    for i in range(numIters):
        (fx, vk) = Oprf.evaluate(privk, publk, x)
    endTimer("Oprf::evaluate", start, numIters)

    start = startTimer()
    for i in range(numIters):
        digest = Oprf.unblind(fx, vk, r)
    endTimer("Oprf::unblind", start, numIters)
    
def bench_voprf():
    callDetails = "+123456789|+1987654321|1733427398"
    (sk, pk) = Voprf.keygen()

    # Check for correctness first
    (p1, x1, r1) = Voprf.blind(msg=callDetails)
    (p2, x2, r2) = Voprf.blind(msg=callDetails)
    assert(p1 == p2) # hashed points must match
    assert(x1 != x2) # blindings must differ
    assert(r1 != r2) # random scalars must differ
    
    fx1 = Voprf.evaluate(sk=sk, x=x1)
    fx2 = Voprf.evaluate(sk=sk, x=x2)
    assert(fx1 != fx2)
    
    digest1 = Voprf.unblind(fx=fx1, r=r1)
    digest2 = Voprf.unblind(fx=fx2, r=r2)
    assert(digest1 == digest2)
    
    assert(Voprf.verify(pk=pk, p=p1, y=digest1))
    assert(Voprf.verify(pk=pk, p=p2, y=digest2))

    start = startTimer()
    for i in range(numIters):
        (p, x, r) = Voprf.blind(msg=callDetails)
    endTimer("Voprf::blind", start, numIters)

    start = startTimer()
    for i in range(numIters):
        fx = Voprf.evaluate(sk=sk, x=x)
    endTimer("Voprf::evaluate", start, numIters)

    start = startTimer()
    for i in range(numIters):
        digest = Voprf.unblind(fx=fx, r=r)
    endTimer("Voprf::unblind", start, numIters)
    
    start = startTimer()
    for i in range(numIters):
        assert Voprf.verify(pk=pk, p=p, y=digest)
    endTimer("Voprf::verify", start, numIters)

def bench_ciphering():
    key = Ciphering.keygen()
    plaintext = Utils.random_bytes(256) # 2KB

    start = startTimer()
    for i in range(numIters):
        ctx = Ciphering.enc(key, plaintext)
    endTimer("Ciphering::enc", start, numIters)

    start = startTimer()
    for i in range(numIters):
        dec_msg: bytes = Ciphering.dec(key, ctx)
    endTimer("Ciphering::dec", start, numIters)

    # check correctness
    assert(plaintext == dec_msg)

def key_rotation():
    # Ensure KeyRotation is a singleton
    instance1 = KeyRotation.get_instance()
    instance2 = KeyRotation.get_instance()
    assert(instance1 == instance2)
    list_size = 4
    interval = 1 # seconds
    instance1.start_rotation(list_size, interval)
    keyidx = 0

    (sk, pk) = instance1.get_key(keyidx)
    print(f"\nKeyRotation\nKey at {keyidx}: ", Utils.to_base64(sk))

    # Key rotation works well if after every list_size * interval seconds, key at keyidx changes
    for i in range(100):
        time.sleep(1)
        (sk, pk) = instance1.get_key(0)
        print(f"after {i+1} second, key at 0: ", Utils.to_base64(sk))
    
    instance1.stop_rotation()

def main():
    bench_ciphering()
    bench_oprf()
    # key_rotation()
    bench_voprf()

if __name__ == "__main__":
    main()