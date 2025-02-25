from cpex.helpers import http
import asyncio, time

data = {
    "x": "nlLYZx9RgnxnG2oVYVRv6o2mAEAv0f78h2/D5tvzb3Q=",
    "i_k": 5,
    "sig": "ATAAAAB7F4liThxebzDS+pqU7DwzKJCyjTaKsEeiqE1++r2yjWuD5RsLre4wQiQv8Mkj0xkwAAAAKuJkYv4cve10Hr0DBp5KFDfI8RktANuO1pQHaKbp1yRS14kUUg60Pvo4+ck21S8SMAAAAMuJwg49B2d0bdymhNshpHtYh+H2S4XyinQLueaDt+MV29SuJ7ck1kA8WRcUHPT6BCAAAAA3w1Y7RgcG2sIUMAK+vrxSzoDBP2TkCc4d7tfXNk6cPSAAAACHxbWHITbtWodmbqNJuqc4axodyMq/jClJLWXybncGAyAAAABti3YQuZZI0wieglUC5j5rPcdLMq76A9sBnBnd+sXDKyAAAACvk5QWR3z4z2t+LZRC6gwNNd4RSoZTorE6ZFWRqPIDOSAAAABVZsfkDNSIqBA1FdpV0d6BgPFO0P6SIB70Jw6ivPBsIyAAAACR1E3g/gvG/mkuH+Bi7IFV+B2s6hENleRguWxi9Lu5CQ=="
}

async def main():
    reqs = [
        {
            'url': 'http://54.90.184.228:10430/evaluate',
            'data': data
        },
        {
            'url': 'http://3.87.17.75:10430/evaluate',
            'data': data
        },
        {
            'url': 'http://34.201.218.218:10430/evaluate',
            'data': data
        }
    ]

    start_race = time.perf_counter()
    res, session, pending = await http.posts_race(reqs)
    end_race = time.perf_counter() - start_race

    # start_posts = time.perf_counter()
    # all_res = await http.posts(reqs)
    # end_posts = time.perf_counter() - start_posts
    
    # print(f"Time Taken for posts", end_posts * 1000)
    print(f"Time Taken for race", end_race * 1000)

    print('Post Race', res)
    print('Pending', pending)
    await session.close()

if __name__ == '__main__':
    asyncio.run(main())