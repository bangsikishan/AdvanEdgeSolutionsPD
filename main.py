import os
import re
import sys
import time

from selenium.webdriver.common.by import By

sys.path.append(os.getcwd())
from utils import (  # noqa
    check_date,
    check_for_duplicate_amr_hash,
    create_database_session,
    generate_md5_hash,
    get_env_variables,
    initialize_webdriver,
    insert_to_amr_database,
    parse_date,
)

script_path = os.path.abspath(__file__)
script_directory = os.path.dirname(script_path)
env_path = os.path.join(script_directory, ".env")
[
    ecgains,
    _,
    base_url,
    executable_path,
    _,
    _,
    _,
    browser_type,
    smi_data_url,
    _,
    _,
    _,
    _,
    _,
] = get_env_variables(env_path=env_path)

driver = initialize_webdriver(
    exec_path=executable_path,
    browser_type=browser_type,
    download_dir=None,
    is_headless=True,
)

db_session = create_database_session(database_url=smi_data_url)

driver.get(base_url)

pattern = r"~#~docId~#~:~#~(.*?)~#~"

try:
    time.sleep(10)
    iframe = driver.find_element(
        By.XPATH,
        "/html/body/div[1]/div/div[3]/div/main/div/div/div/div[2]/div/div/div/section/div[2]/div/section[2]/div[2]/div/div[2]/div/div[2]/iframe",
    )

    driver.switch_to.frame(iframe)

    tbody = driver.find_element(By.XPATH, "//*[@id='theTable']/tbody")
    bid_elements = tbody.find_elements(By.XPATH, "./*")

    for bid_element in bid_elements:
        driver.execute_script("arguments[0].scrollIntoView(true);", bid_element)
        time.sleep(1)

        bid_due_date = bid_element.find_element(By.XPATH, ".//td[5]").text.strip()
        if "" == bid_due_date:
            continue

        parsed_due_date = parse_date(date=bid_due_date)

        if check_date(date=parsed_due_date):
            continue

        bid_id = bid_element.find_element(By.XPATH, ".//td[3]").text.strip()
        bid_title = bid_element.find_element(By.XPATH, ".//td[2]").text.strip()

        link_text = bid_element.find_element(By.XPATH, ".//td[6]/a").get_attribute(
            "onclick"
        )

        match = re.search(pattern, link_text)

        if match:
            link = f"https://www.advanedgesolutions.com/_files/{match.group(1)}"

        # BID NO + TITLE + DUE DATE
        hash = generate_md5_hash(
            ecgain=bid_id, bidno=bid_title, filename=parsed_due_date
        )

        if check_for_duplicate_amr_hash(session=db_session, hash=hash):
            continue

        insert_to_amr_database(
            session=db_session,
            ecgain=ecgains,
            number=bid_id,
            title=bid_title,
            due_date=parsed_due_date if parsed_due_date else None,
            hash=hash,
            url1=base_url,
            url2=link if link else None,
            description=bid_title,
        )
except Exception as e:
    print("[-] Exception thrown!")
    print(e)

driver.switch_to.default_content()
driver.quit()
print(f"[+] End of script {script_path}!")