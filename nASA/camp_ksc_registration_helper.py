"""
Camp KSC 2026 

"""

import webbrowser
import time
from datetime import datetime
import json
import os

# 
REGISTRATION_OPEN_DATE = "2026-01-21"
REGISTRATION_URL = "https://www.kennedyspacecenter.com/camps-and-education/programs/camp-kennedy-space-center/"

class CampKSCHelper:
    def __init__(self):
        self.config_file = "camp_ksc_config.json"
        self.load_config
    
    def load_config(self):
        """"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = {}
    
    def save_config(self):
        """"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def setup_registration_info(self):
        """"""
        print("=" * 60)
        print("Camp KSC 2026 ")
        print("=" * 60)
        
        # 
        print("\n【】")
        camper_name = input(": ").strip
        birthdate = input(" (YYYY-MM-DD): ").strip
        
        # 
        age_group = self.determine_age_group(birthdate)
        print(f"✓ : {age_group}")
        
        # 
        print("\n【】")
        print(":")
        weeks = {
            "1": "Week 1: 525 - 529",
            "2": "Week 2: 61 - 65",
            "3": "Week 3: 68 - 612",
            "4": "Week 4: 615 - 619",
            "5": "Week 5: 622 - 626",
            "6": "Week 6: 629 - 73",
            "7": "Week 7: 76 - 710",
            "8": "Week 8: 713 - 717",
            "9": "Week 9: 720 - 724",
            "10": "Week 10: 727 - 731"
        }
        for key, value in weeks.items:
            print(f"  {key}. {value}")
        
        selected_weeks = input("\n (，: 1,2,3): ").strip
        selected_weeks_list = [w.strip for w in selected_weeks.split(',')]
        
        # 
        print("\n【】")
        guardians_list = []
        while True:
            guardian_name = input(" : ").strip
            if not guardian_name:
                break
            guardian_relation = input("   (: mother/father): ").strip
            guardian_email = input("  : ").strip
            guardian_phone = input("   : ").strip
            guardians_list.append({
                "name": guardian_name,
                "relation": guardian_relation,
                "email": guardian_email,
                "phone": guardian_phone
            })
            add_more = input("  ? (y/n): ").strip.lower
            if add_more != 'y':
                break
        
        # 
        self.config = {
            "camper": {
                "name": camper_name,
                "birthdate": birthdate,
                "age_group": age_group
            },
            "selected_weeks": selected_weeks_list,
            "guardians": guardians_list,
            "registration_date": REGISTRATION_OPEN_DATE
        }
        
        self.save_config
        print("\n✓ ！")
        self.show_summary
    
    def determine_age_group(self, birthdate):
        """"""
        try:
            birth = datetime.strptime(birthdate, "%Y-%m-%d")
            birth_year = birth.year
            birth_month = birth.month
            birth_day = birth.day
            
            # （202661）
            if (birth_year == 2017 and birth_month >= 6) or \
               (birth_year == 2018) or \
               (birth_year == 2019 and birth_month <= 5):
                return "PATHFINDER"
            elif (birth_year == 2015 and birth_month >= 6) or \
                 (birth_year == 2016) or \
                 (birth_year == 2017 and birth_month <= 5):
                return "SPIRIT"
            elif (birth_year == 2013 and birth_month >= 6) or \
                 (birth_year == 2014) or \
                 (birth_year == 2015 and birth_month <= 5):
                return "OPPORTUNITY"
            elif (birth_year == 2009 and birth_month >= 6) or \
                 (birth_year in [2010, 2011, 2012]) or \
                 (birth_year == 2013 and birth_month <= 5):
                return "INGENUITY"
            else:
                return "，"
        except:
            return ""
    
    def set_info_directly(self, camper_name, birthdate_str, selected_weeks_list, guardians_list):
        """"""
        # （ MM/DD/YYYY  YYYY-MM-DD）
        birthdate = self.normalize_date(birthdate_str)
        if not birthdate:
            print(f"： {birthdate_str}")
            return False
        
        # 
        age_group = self.determine_age_group(birthdate)
        
        # 
        self.config = {
            "camper": {
                "name": camper_name,
                "birthdate": birthdate,
                "age_group": age_group
            },
            "selected_weeks": selected_weeks_list if isinstance(selected_weeks_list, list) else [str(selected_weeks_list)],
            "guardians": guardians_list if isinstance(guardians_list, list) else [guardians_list],
            "registration_date": REGISTRATION_OPEN_DATE
        }
        
        self.save_config
        print("\n✓ ！")
        self.show_summary
        return True
    
    def normalize_date(self, date_str):
        """ YYYY-MM-DD"""
        try:
            #  MM/DD/YYYY 
            if '/' in date_str:
                parts = date_str.split('/')
                if len(parts) == 3:
                    month, day, year = parts
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            #  YYYY-MM-DD 
            elif '-' in date_str:
                datetime.strptime(date_str, "%Y-%m-%d")
                return date_str
        except:
            pass
        return None
    
    def show_summary(self):
        """"""
        if not self.config:
            print("\n。。")
            return
        
        print("\n" + "=" * 60)
        print("")
        print("=" * 60)
        print(f": {self.config.get('camper', {}).get('name', 'N/A')}")
        print(f": {self.config.get('camper', {}).get('birthdate', 'N/A')}")
        print(f": {self.config.get('camper', {}).get('age_group', 'N/A')}")
        
        weeks = self.config.get('selected_weeks', [])
        if weeks:
            if weeks == ['all'] or 'all' in weeks:
                print(f": ")
            else:
                print(f": {', '.join(weeks)}")
        else:
            print(f": ")
        
        # 
        guardians = self.config.get('guardians', [])
        if not guardians:
            # 
            guardian = self.config.get('guardian', {})
            if guardian:
                guardians = [guardian]
        
        if guardians:
            print(f"\n:")
            for i, guardian in enumerate(guardians, 1):
                if isinstance(guardian, dict):
                    print(f"  {i}. {guardian.get('name', 'N/A')} ({guardian.get('relation', '')})")
                    print(f"     : {guardian.get('email', 'N/A')}")
                    if guardian.get('phone'):
                        print(f"     : {guardian.get('phone', '')}")
        
        print("=" * 60)
    
    def countdown_to_registration(self):
        """"""
        target_date = datetime.strptime(REGISTRATION_OPEN_DATE, "%Y-%m-%d")
        target_date = target_date.replace(hour=0, minute=0, second=0)
        now = datetime.now
        
        if now < target_date:
            delta = target_date - now
            days = delta.days
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            print("\n" + "=" * 60)
            print(":")
            print(f"  {days}  {hours}  {minutes}  {seconds} ")
            print("=" * 60)
        else:
            print("\n！！")
    
    def open_registration_page(self):
        """"""
        print(f"\n: {REGISTRATION_URL}")
        webbrowser.open(REGISTRATION_URL)
        print("✓ ")
    
    def show_checklist(self):
        """"""
        print("\n" + "=" * 60)
        print("")
        print("=" * 60)
        print("□ ")
        print("□ ")
        print("□ ")
        print("□ ")
        print("□ ")
        print("□ ")
        print("□ 5-10")
        print("=" * 60)
        print("\n:")
        print("• ，")
        print("• ，")
        print("• ，")
        print("• ，")
        print("=" * 60)

def main:
    helper = CampKSCHelper
    
    # ，
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--set-shawn":
        # Shawn Huang
        print("Shawn Huang...")
        success = helper.set_info_directly(
            camper_name="Shawn Huang",
            birthdate_str="09/27/2016",
            selected_weeks_list=["all"],  # 
            guardians_list=[
                {
                    "name": "Na Lu",
                    "relation": "mother",
                    "email": "christina600@gmail.com",
                    "phone": ""
                },
                {
                    "name": "Jing Huang",
                    "relation": "father",
                    "email": "mail.jing.huang@gmail.com",
                    "phone": ""
                }
            ]
        )
        if success:
            print("\n✓ ！")
            print("\n：")
            print("• ")
            print("• ")
            print("• ：$450 + ")
            print("• ")
        return
    
    while True:
        print("\n" + "=" * 60)
        print("Camp KSC 2026 ")
        print("=" * 60)
        print("1. ")
        print("2. ")
        print("3. ")
        print("4. ")
        print("5. ")
        print("6. ")
        print("=" * 60)
        
        choice = input("\n (1-6): ").strip
        
        if choice == "1":
            helper.setup_registration_info
        elif choice == "2":
            helper.show_summary
        elif choice == "3":
            helper.countdown_to_registration
        elif choice == "4":
            helper.open_registration_page
        elif choice == "5":
            helper.show_checklist
        elif choice == "6":
            print("\n！！")
            break
        else:
            print("\n，。")

if __name__ == "__main__":
    main
