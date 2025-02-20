import random
from cpex import config
from locust import task, FastHttpUser, between
from cpex.helpers import files, mylogging

items = files.read_json(config.CONF_DIR + "/loads.json", default=[])
mylogging.init_mylogger(name='locust', filename='logs/locust.log')
mylogging.mylogger.debug(f'Loaded {len(items)} items from loads.json')

class CPSLoad(FastHttpUser):
    wait_time = between(1, 2)

    @task
    def publish(self):
        try:
            item = items[0]
            headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer ' + item['atis']['pub_bearer']}
            data = {'passports': [item['passport']]}
            with self.rest("POST", item['atis']['pub_url'], name=item['atis']['pub_name'], json=data, headers=headers) as res:
                if res.js is None:
                    pass
        except Exception as e:
            raise e
