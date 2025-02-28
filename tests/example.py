from cpex.helpers import http
import asyncio, time, json
from cpex.prototype.stirshaken import certs

creds = json.load(open('conf/certs.json'))
certs.set_certificate_repository(creds)
certificate = "-----BEGIN CERTIFICATE-----\nMIIBhzCCAS2gAwIBAgIUY9zn5EOXoYys4LorBxhEDlerq4swCgYIKoZIzj0EAwIw\nQzELMAkGA1UEBhMCVVMxEDAOBgNVBAgMB0FsYWJhbWExEjAQBgNVBAoMCU9SRyBp\nY2EtMTEOMAwGA1UEAwwFaWNhLTEwHhcNMjUwMjI4MjMzOTE4WhcNMjYwMjI4MjMz\nOTE4WjBEMQswCQYDVQQGEwJVUzENMAsGA1UECAwESW93YTEUMBIGA1UECgwLT1JH\nIG9jcnQtMjkxEDAOBgNVBAMMB29jcnQtMjkwWTATBgcqhkjOPQIBBggqhkjOPQMB\nBwNCAARXuyFvhdlkTLQqSCu2UB6CVFJwA0+ncJufU9Mpa6X+0AG43NvOm2ERs9O2\n1rNQrJ1GDmnR+5TMn8eSD3cI5GAcMAoGCCqGSM49BAMCA0gAMEUCIQDXxRVF/Ayp\nQKvUX30POPYcEfmAj5sKRLF1Q9IXbeJVTwIgf7t7KAXV15KRxmy1p5mxZ3iix50c\nF0y4lXULw/fIsAU=\n-----END CERTIFICATE-----\n"

async def main():
    iters = 100
    start = time.perf_counter()
    for i in range(iters):
        certs.verify_chain_of_trust(certificate)
    elapsed = (time.perf_counter() - start) * 1000 / iters
    print(f"Elapsed time: {elapsed:0.2f} ms")

if __name__ == '__main__':
    asyncio.run(main())