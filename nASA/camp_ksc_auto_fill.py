"""
Camp KSC 2026 （Selenium）
⚠️ ：，
⚠️ ：，
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import json
import time
import os

# 
CONFIG_FILE = "camp_ksc_config.json"

def load_config:
    """"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def setup_driver(headless=False):
    """Chrome"""
    chrome_options = Options
    if headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get:  => undefined})")
        return driver
    except Exception as e:
        print(f"：。ChromeChromeDriver。")
        print(f"：{e}")
        return None

def wait_for_queue(driver, timeout=600):
    """"""
    print("...")
    try:
        # 
        # 
        WebDriverWait(driver, timeout).until(
            lambda d: "queue" not in d.current_url.lower or 
                     d.find_elements(By.TAG_NAME, "form")
        )
        print("✓ ")
        return True
    except:
        print("⚠️ ，")
        return False

def fill_registration_form(driver, config):
    """"""
    wait = WebDriverWait(driver, 30)
    
    try:
        camper = config.get('camper', {})
        guardians = config.get('guardians', [])
        
        print("\n...")
        
        # ：，HTML
        # ID、nameclass
        
        # 
        try:
            first_name_field = wait.until(
                EC.presence_of_element_located((By.NAME, "camper_first_name"))
            )
            name_parts = camper.get('name', '').split
            if len(name_parts) >= 2:
                first_name_field.send_keys(name_parts[0])
                driver.find_element(By.NAME, "camper_last_name").send_keys(' '.join(name_parts[1:]))
            else:
                first_name_field.send_keys(camper.get('name', ''))
            print("✓ ")
        except Exception as e:
            print(f"⚠️ ：{e}")
        
        # 
        try:
            birthdate = camper.get('birthdate', '')
            if birthdate:
                #  YYYY-MM-DD
                year, month, day = birthdate.split('-')
                Select(driver.find_element(By.NAME, "birth_month")).select_by_value(month.lstrip('0'))
                Select(driver.find_element(By.NAME, "birth_day")).select_by_value(day.lstrip('0'))
                Select(driver.find_element(By.NAME, "birth_year")).select_by_value(year)
            print("✓ ")
        except Exception as e:
            print(f"⚠️ ：{e}")
        
        # 
        if guardians:
            guardian = guardians[0]  # 
            try:
                driver.find_element(By.NAME, "guardian_name").send_keys(guardian.get('name', ''))
                driver.find_element(By.NAME, "guardian_email").send_keys(guardian.get('email', ''))
                if guardian.get('phone'):
                    driver.find_element(By.NAME, "guardian_phone").send_keys(guardian.get('phone', ''))
                print("✓ ")
            except Exception as e:
                print(f"⚠️ ：{e}")
        
        # 
        try:
            selected_weeks = config.get('selected_weeks', [])
            if selected_weeks and selected_weeks != ['all']:
                # 
                week_select = Select(driver.find_element(By.NAME, "camp_week"))
                # 
                week_select.select_by_index(1)  # 
            print("✓ ")
        except Exception as e:
            print(f"⚠️ ：{e}")
        
        print("\n⚠️ ：，：")
        print("1. ")
        print("2. （，）")
        print("3. ")
        print("4. ")
        
        # 
        input("\n...")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ：{e}")
        print("")
        return False

def main:
    """"""
    print("=" * 60)
    print("Camp KSC 2026 ")
    print("=" * 60)
    print("\n⚠️ ：")
    print("1. ，")
    print("2. ")
    print("3. ")
    print("4. ")
    print("=" * 60)
    
    # 
    config = load_config
    if not config:
        print("\n❌ ， camp_ksc_registration_helper.py ")
        return
    
    print("\n：")
    print(f"  ：{config.get('camper', {}).get('name', 'N/A')}")
    print(f"  ：{config.get('camper', {}).get('age_group', 'N/A')}")
    
    # 
    confirm = input("\n？(y/n): ").strip.lower
    if confirm != 'y':
        print("")
        return
    
    # 
    print("\n...")
    driver = setup_driver(headless=False)  # ，
    if not driver:
        return
    
    try:
        # 
        url = "https://www.kennedyspacecenter.com/camps-and-education/programs/camp-kennedy-space-center/"
        print(f"\n：{url}")
        driver.get(url)
        
        # 
        print("\n'Join the Queue'，...")
        input("，...")
        
        # 
        fill_registration_form(driver, config)
        
        print("\n✓ ")
        print("")
        
    except KeyboardInterrupt:
        print("\n\n")
    except Exception as e:
        print(f"\n❌ ：{e}")
    finally:
        # 
        close = input("\n？(y/n): ").strip.lower
        if close == 'y':
            driver.quit
        else:
            print("，")

if __name__ == "__main__":
    main
