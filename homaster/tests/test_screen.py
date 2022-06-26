from django.test import LiveServerTestCase
from get_chrome_driver import GetChromeDriver
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

get_driver = GetChromeDriver()
get_driver.install()

class IntegrationTest(LiveServerTestCase):
    # fixtures = ['user-data.json']

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        options = Options()
        options.headless = True
        cls.selenium = webdriver.Chrome(options=options)
        cls.wait = WebDriverWait(cls.selenium, 30)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_gm(self):
        """
        GMの一連の操作をテスト
        ①ENGAWAを設える（メールアドレスなし）
        ②ハンドアウトの追加
            各種別2枚ずつ作る
            PC/PL名あり・なし
        ③PL招待
        ④秘密確認（PL画面）
        ⑤閲覧権限管理
        ⑥秘密確認（PL画面）
        ⑦セッション終了
        """
        # ENGAWAを設える
        self.selenium.get(f'{self.live_server_url}/index')
        scenario_name = self.selenium.find_element(by=By.ID, value="id_scenario_name")
        scenario_name.send_keys('Selenium Test')
        self.selenium.find_element(by=By.CLASS_NAME, value='btn-primary').click()
        self.wait.until(EC.presence_of_element_located((By.XPATH, "//p[contains(@class, 'scenario-name')]")))

        # ENGAWA確認
        # タイトル確認
        self.assertEqual(self.selenium.title, 'Selenium Test - Shinobi-Mas')
        # ヘッダ確認
        header_gm = self.selenium.find_element(by=By.TAG_NAME, value='header')
        self.assertEqual(header_gm.text, "あなたはGMです。")
