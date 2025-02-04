from cpex.prototype.experiments.results.scripts import helpers


if __name__ == "__main__":
    file_path = "cpex/prototype/experiments/results/experiment-2.csv"
    columns = ['PUB:P', 'PUB:EV', 'PUB:MS', 'RET:P', 'RET:MS']
    stats = helpers.compute_statistics(file_path, columns)
    n_std, rate, n_ev, n_ms = 1, 10000, 20, 20
    stats = helpers.estimate_vcpus(
        stats=stats,
        n_std=n_std, 
        rate=rate, 
        n_ev=n_ev, 
        n_ms=n_ms
    )
    print(stats)
