import uuid
from django.test import TestCase
from django.urls import reverse
from django.core import mail

from homaster.tests.factories import *
from homaster.models import *

class SingInTest(TestCase):
    def test_ok_pl(self):
        pl = PlayerFactory(email=None, role=0)
        uuid = pl.engawa.uuid
        p_code = pl.p_code
        url = f'/{uuid}?p_code={p_code}'
        res = self.client.get(url)
        self.assertRedirects(res, '/engawa')

    def test_ok_gm(self):
        pl = PlayerFactory()
        uuid = pl.engawa.uuid
        p_code = pl.p_code
        url = f'/{uuid}?p_code={p_code}'
        res = self.client.get(url)
        self.assertRedirects(res, '/engawa')

    def test_ok_gm_interim(self):
        """
        仮登録のGMの場合，roleの更新とメール送信を行う
        """
        pl = PlayerFactory(role=2)
        uuid = pl.engawa.uuid
        p_code = pl.p_code
        url = f'/{uuid}?p_code={p_code}'
        res = self.client.get(url)
        # DBの更新を反映
        pl.refresh_from_db()
        self.assertEqual(pl.role, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [pl.email])
        self.assertEqual(mail.outbox[0].subject, "【Shinobo-Mas】登録完了のお知らせ")
        self.assertRedirects(res, '/engawa')

    def test_ng_without_pcode(self):
        """
        クエリパラメータにp_codeがなければ，
        エラーログを出力してトップページへリダイレクト
        """
        url = f"/{uuid.uuid4()}"
        with self.assertLogs('homaster.views', level='ERROR') as cm:
            res = self.client.get(url)
        self.assertIn("There is not p_code in query string.", cm.output[0])
        self.assertRedirects(res, '/index')

    def test_ng_wrong_query(self):
        """
        uuidとp_codeの組み合わせがDBに存在しない場合，
        エラーログを出力してトップページへリダイレクト
        """
        e_uuid = uuid.uuid4()
        url = f"/{e_uuid}?p_code=00000000"
        with self.assertLogs('homaster.views', level='ERROR') as cm:
            res = self.client.get(url)
        err_str = f"There is not a player with p_code 00000000 in ENGAWA {e_uuid}"
        self.assertIn(err_str, cm.output[0])
        self.assertRedirects(res, '/index')

class DeleteHandoutTest(TestCase):
    def test_ok(self):
        """
        ハンドアウト削除を行う。
        紐づくPlayerとAuthも削除される。
        """
        # ログイン
        c = self.client
        gm = logined_user(c)
        c.get('/engawa')

        # PC1とそれに紐づくPLとAuthを作成
        pc1 = HandoutFactory(engawa=gm.engawa, hidden=False)
        pl = PlayerFactory(email=None, engawa=gm.engawa, handout=pc1)
        auth1 = AuthFactory(player=pl, handout=pc1, auth_back=True)

        # HO1とそれに紐づくPLのAuth
        ho1 = HandoutFactory(engawa=gm.engawa, hidden=False, type=3)
        auth2 = AuthFactory(player=pl, handout=ho1)

        self.assertEqual(Handout.objects.filter(engawa=gm.engawa).count(), 2)
        self.assertEqual(Player.objects.filter(engawa=gm.engawa).count(), 2)
        self.assertEqual(Auth.objects.filter(player=pl).count(), 2)

        # PC1を削除
        res = c.get(f'/delete?id={pc1.id}')
        self.assertRedirects(res, '/engawa')
        self.assertEqual(Handout.objects.filter(engawa=gm.engawa).count(), 1)
        self.assertEqual(Player.objects.filter(engawa=gm.engawa).count(), 1)
        self.assertEqual(Auth.objects.filter(player=pl).count(), 0)

    def test_ng_not_login(self):
        """
        ログインユーザでなければトップページにリダイレクトする
        """
        res = self.client.get('/delete?id=1')
        self.assertRedirects(res, '/index')

    def test_ng_not_gm(self):
        """
        ログイン済でもGMでなければ404エラーを返す
        """
        # ログイン
        c = self.client
        pl = logined_user(c, 0)
        c.get('/engawa')

        HandoutFactory(engawa=pl.engawa)
        with self.assertLogs('homaster.views', level='ERROR') as cm:
            res = self.client.get("/delete?id=1")
        err = f"This player with p_code {pl.p_code} is not GM."
        self.assertIn(err, cm.output[0])
        self.assertEqual(res.status_code, 404)

    def test_404_no_ho(self):
        """
        DBにid=pkのハンドアウトがなければ404エラー
        """
        # ログイン
        c = self.client
        logined_user(c)
        c.get('/engawa')

        # 他所のENGAWAにハンドアウトを作成
        HandoutFactory()
        # ID=1のハンドアウトが存在することを確認
        self.assertTrue(Handout.objects.get(id=1))

        res = self.client.get('/delete?id=2')
        self.assertEqual(res.status_code, 404)

    def test_404_other_engawa(self):
        """
        ログイン中のENGAWAにid=pkのハンドアウトがなければ404エラー
        """
        # ログイン
        c = self.client
        gm = logined_user(c)
        c.get('/engawa')

        # 他所のENGAWAにハンドアウトを作成
        HandoutFactory()
        # ID=1のハンドアウトが存在することを確認
        self.assertTrue(Handout.objects.get(id=1))

        with self.assertLogs('homaster.views', level='ERROR') as cm:
            res = self.client.get('/delete?id=1')
        err = f"This player with p_code {gm.p_code} cannot delete a handout(ID: 1) of other ENGAWA."
        self.assertIn(err, cm.output[0])
        self.assertEqual(res.status_code, 404)

class CloseEngawaTest(TestCase):
    def test_ok(self):
        """
        ENGAWAを削除するとクローズ完了画面へ遷移する
        ENGAWAに紐づく他のテーブルのレコードも削除される
        """
        # ログイン
        c = self.client
        gm = logined_user(c)
        c.get('/engawa')

        # PC1とそれに紐づくPLとAuthを作成
        pc1 = HandoutFactory(engawa=gm.engawa, hidden=False)
        pl = PlayerFactory(email=None, engawa=gm.engawa, handout=pc1)
        auth1 = AuthFactory(player=pl, handout=pc1, auth_back=True)

        # HO1とそれに紐づくPLのAuth
        ho1 = HandoutFactory(engawa=gm.engawa, hidden=False, type=3)
        auth2 = AuthFactory(player=pl, handout=ho1)

        self.assertEqual(Engawa.objects.filter(uuid=gm.engawa.uuid).count(), 1)
        self.assertEqual(Handout.objects.filter(engawa=gm.engawa).count(), 2)
        self.assertEqual(Player.objects.filter(engawa=gm.engawa).count(), 2)
        self.assertEqual(Auth.objects.filter(player=pl).count(), 2)

        # ENGAWAを削除
        res = c.get(f'/close')
        self.assertRedirects(res, '/close-success')
        self.assertEqual(Engawa.objects.filter(uuid=gm.engawa.uuid).count(), 0)
        self.assertEqual(Handout.objects.filter(engawa=gm.engawa).count(), 0)
        self.assertEqual(Player.objects.filter(engawa=gm.engawa).count(), 0)
        self.assertEqual(Auth.objects.filter(player=pl).count(), 0)

    def test_ng_not_login(self):
        """
        ログインユーザでなければトップページにリダイレクトする
        """
        res = self.client.get('/close')
        self.assertRedirects(res, '/index')

    def test_ng_not_gm(self):
        """
        ログイン済でもGMでなければ404エラーを返す
        """
        # ログイン
        c = self.client
        pl = logined_user(c, 0)
        c.get('/engawa')

        HandoutFactory(engawa=pl.engawa)
        with self.assertLogs('homaster.views', level='ERROR') as cm:
            res = self.client.get("/close")
        err = f"This player with p_code {pl.p_code} is not GM."
        self.assertIn(err, cm.output[0])
        self.assertEqual(res.status_code, 404)

class AfterCloseViewTest(TestCase):
    def test_get(self):
        res = self.client.get(reverse('homaster:close-success'))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'homaster/thanks.html')

class InterimViewTest(TestCase):
    def test_get(self):
        res = self.client.get(reverse('homaster:interim'))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'homaster/interim.html')

class IndexViewTest(TestCase):
    def test_get(self):
        res = self.client.get(reverse('homaster:index'))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'homaster/index.html')

    def test_post_without_email(self):
        """
        メールアドレスを入力しない場合，ENGAWAとGMを作成して
        一覧画面へリダイレクト
        """
        s_name = "test_post_without_email"
        post_data = {
            "scenario_name": s_name,
            "email": "",
        }
        res = self.client.post(reverse('homaster:index'), post_data, follow=True)
        self.assertEqual(Engawa.objects.filter(scenario_name=s_name).count(), 1)
        self.assertEqual(Player.objects.filter(role=1).count(), 1)
        self.assertEqual(Player.objects.filter(role=1).first().engawa.scenario_name, s_name)
        self.assertEqual(len(mail.outbox), 0)
        self.assertRedirects(res, '/engawa')

    def test_post_with_unique_email(self):
        """
        未登録のメールアドレスを入力した場合，ENGAWAとGMを作成して
        仮登録完了メールを送信し，仮登録完了画面へリダイレクト。
        同じアドレスを持った仮登録のGMが存在しても影響を受けない。
        """
        s_name = "test_post_with_unique_email"
        address = "with.unique.email@example.com"
        post_data = {
            "scenario_name": s_name,
            "email": address,
        }
        # 同じアドレスを持った仮登録のGMを作成
        PlayerFactory(email=address, role=2)
        res = self.client.post(reverse('homaster:index'), post_data, follow=True)
        self.assertEqual(Engawa.objects.filter(scenario_name=s_name).count(), 1)
        self.assertEqual(Player.objects.filter(role=2).count(), 2)
        gm = Player.objects.filter(role=2).last()
        e_uuid = gm.engawa.uuid
        p_code = gm.p_code
        url = f"https://None/{e_uuid}?p_code={p_code}"
        self.assertEqual(gm.engawa.scenario_name, s_name)
        self.assertEqual(gm.email, address)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [address])
        self.assertIn("仮登録" ,mail.outbox[0].subject)
        self.assertIn(s_name ,mail.outbox[0].body)
        self.assertIn(url ,mail.outbox[0].body)
        self.assertRedirects(res, '/interim')

    def test_post_with_existing_email(self):
        """
        登録済のメールアドレスを入力した場合，ENGAWAとGMを作成して
        登録完了メールを送信し，一覧画面へリダイレクト
        """
        s_name = "test_post_with_existing_email"
        address = "with.existing.email@example.com"
        post_data = {
            "scenario_name": s_name,
            "email": address,
        }
        # 正式登録済みのGMを作成
        PlayerFactory(email=address)
        res = self.client.post(reverse('homaster:index'), post_data, follow=True)
        self.assertEqual(Engawa.objects.filter(scenario_name=s_name).count(), 1)
        self.assertEqual(Player.objects.filter(role=1).count(), 2)
        gm = Player.objects.filter(role=1).last()
        self.assertEqual(gm.engawa.scenario_name, s_name)
        self.assertEqual(gm.email, address)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [address])
        self.assertIn("【Shinobo-Mas】登録完了のお知らせ" ,mail.outbox[0].subject)
        self.assertIn(s_name ,mail.outbox[0].body)
        self.assertRedirects(res, '/engawa')

class ReenterViewTest(TestCase):
    def test_get(self):
        res = self.client.get(reverse('homaster:reenter'))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'homaster/reenter.html')

    def test_post_registered_address(self):
        """
        登録済のアドレスをPOSTすると，そのアドレスで正式登録済のENGAWAの
        URLをすべて含んだ通知メールを送信して同じ画面にリダイレクトする
        """
        address = "registered.address@example.com"
        post_data = {
            "email": address,
        }
        # 仮登録と正式登録済のGMを作成
        gm1 = PlayerFactory(email=address)
        gm2 = PlayerFactory(email=address)
        gm3 = PlayerFactory(email=address, role=2)
        res = self.client.post(reverse('homaster:reenter'), post_data, follow=True)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [address])
        self.assertIn("ENGAWA再訪URL" ,mail.outbox[0].subject)
        for i, gm in enumerate([gm1, gm2, gm3]):
            en = gm.engawa
            line = f"{en.scenario_name}: https://None/{en.uuid}?p_code={gm.p_code}"
            if i != 2:
                self.assertIn(line ,mail.outbox[0].body)
            else:
                # 仮登録のENGAWAは含めない
                self.assertNotIn(line ,mail.outbox[0].body)
        self.assertRedirects(res, '/reenter')

class EngawaViewTest(TestCase):
    def test_get_ng_not_login(self):
        """
        ログインユーザでなければトップページにリダイレクトする
        """
        res = self.client.get(reverse('homaster:engawa'))
        self.assertRedirects(res, '/index')

    def test_get_ok_gm(self):
        """
        ログイン済のGMで一覧画面に遷移できる。
        コンテクストとセッションに適切な値が入っている。
        """
        c = self.client
        gm = PlayerFactory(engawa=EngawaFactory(), handout=None, p_code="testtest")
        engawa = gm.engawa
        npc = HandoutFactory(engawa=engawa, type=2, p_code=None)
        ho = HandoutFactory(engawa=engawa, type=3, p_code=None)
        pc = HandoutFactory(engawa=engawa, type=1)
        # 別のENGAWA, GM, Handoutを作成
        gm2 = PlayerFactory(engawa=EngawaFactory(), handout=None, p_code="testtest")
        engawa2 = gm2.engawa
        HandoutFactory(engawa=engawa2, type=2, p_code=None)
        login_url = f"/{engawa.uuid}?p_code={gm.p_code}"
        c.get(login_url)
        res = c.get(reverse('homaster:engawa'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['engawa'].uuid.__str__(), engawa.uuid)
        self.assertEqual(res.context['player'], gm)
        self.assertEqual(res.context['role_name'], 'GM')
        self.assertEqual(c.session['role_name'], 'GM')
        self.assertEqual(list(res.context['object_list'].all()), [pc, npc, ho])
        self.assertEqual(c.session['ho_names'], {str(npc.id): 'NPC1', str(ho.id): 'HO1', str(pc.id): 'PC1'})
        ho_names = list(map(lambda obj: obj.ho_name, res.context['object_list']))
        self.assertEqual(ho_names, ['PC1', 'NPC1', 'HO1'])

    def test_get_ok_pl(self):
        """
        ログイン済のPLで一覧画面に遷移できる。
        コンテクストに適切な値が入っている。
        非公開ハンドアウトは除外されるがハンドアウト名はズレない。
        """
        c = self.client
        # GM, PL, Handout, Authを作成
        # pc2のPL,Authは省略
        gm = PlayerFactory(engawa=EngawaFactory(), handout=None, p_code="hogehoge")
        engawa = gm.engawa
        pc1 = HandoutFactory(engawa=engawa, type=1)
        pl = PlayerFactory(email=None, engawa=engawa, handout=pc1, role=0)
        AuthFactory(player=pl, handout=pc1, auth_back=True)
        npc1 = HandoutFactory(engawa=engawa, type=2, hidden=True, p_code=None)
        AuthFactory(player=pl, handout=npc1, auth_front=False)
        npc2 = HandoutFactory(engawa=engawa, type=2, p_code=None)
        AuthFactory(player=pl, handout=npc2)
        ho = HandoutFactory(engawa=engawa, type=3, p_code=None)
        AuthFactory(player=pl, handout=ho)
        pc2 = HandoutFactory(engawa=engawa, type=1)
        AuthFactory(player=pl, handout=pc2)
        # PC1のPLでログイン
        login_url = f"/{pl.engawa.uuid}?p_code={pl.p_code}"
        c.get(login_url)
        res = c.get(reverse('homaster:engawa'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['engawa'].uuid.__str__(), engawa.uuid)
        self.assertEqual(res.context['player'], pl)
        self.assertEqual(res.context['role_name'], 'PC1')
        self.assertEqual(c.session['role_name'], 'PC1')
        self.assertEqual(res.context['object_list'], [pc1, pc2, npc2, ho])
        self.assertEqual(
            c.session['ho_names'],
            {str(npc1.id): 'NPC1', str(npc2.id): 'NPC2', str(ho.id): 'HO1', str(pc1.id): 'PC1', str(pc2.id): 'PC2'})
        ho_names = list(map(lambda obj: obj.ho_name, res.context['object_list']))
        self.assertEqual(ho_names, ['PC1', 'PC2', 'NPC2', 'HO1'])

class CreateHandoutViewTest(TestCase):
    def test_get_ok(self):
        """
        ログイン済のGMで新規作成画面に遷移できる。
        コンテクストに適切な値が入っている。
        """
        c = self.client
        _ = logined_user(c)
        c.get('/engawa')
        res1 = self.client.get("/create?type=1")
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.context['role_name'], 'GM')
        self.assertEqual(res1.context['ho_type'], 'PC')
        res2 = self.client.get("/create?type=2")
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.context['role_name'], 'GM')
        self.assertEqual(res2.context['ho_type'], 'NPC')
        res3 = self.client.get("/create?type=3")
        self.assertEqual(res3.status_code, 200)
        self.assertEqual(res3.context['role_name'], 'GM')
        self.assertEqual(res3.context['ho_type'], 'HO')

    def test_get_ng_not_login(self):
        """
        ログインユーザでなければトップページにリダイレクトする
        """
        res = self.client.get("/create?type=1")
        self.assertRedirects(res, '/index')

    def test_get_ng_not_gm(self):
        """
        ログイン済でもGMでなければ404エラーを返す
        """
        pl = logined_user(self.client, 0)
        with self.assertLogs('homaster.views', level='ERROR') as cm:
            res = self.client.get("/create?type=1")
        err = f"This player with p_code {pl.p_code} is not GM."
        self.assertIn(err, cm.output[0])
        self.assertEqual(res.status_code, 404)

    def test_get_redirect(self):
        """
        クエリパラメータが不正の場合，自動で"1"とする
        """
        _ = logined_user(self.client)
        res = self.client.get("/create")
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, "/create?type=1")
        res2 = self.client.get("/create?type=5")
        self.assertEqual(res2.status_code, 302)
        self.assertEqual(res2.url, "/create?type=1")

    def test_post_simple(self):
        """
        POSTすると一覧画面にリダイレクトする
        """
        c = self.client
        gm = logined_user(c)
        c.get('/engawa')
        pc1 = HandoutFactory.build(engawa=gm.engawa, hidden=False)
        data_pc1 = create_ho_data_from_factory(pc1)
        res1 = self.client.post('/create?type=1', data_pc1)
        self.assertRedirects(res1, '/engawa')

    def test_post_complex(self):
        """
        ハンドアウトを作成すると，Handout, Player, Authが作成される
        PC, HO(公開), PC, NPC(非公開)の順に作成
        """
        # ログイン
        c = self.client
        gm = logined_user(c)
        c.get('/engawa')

        # PC1を作成
        pc1 = HandoutFactory.build(engawa=gm.engawa, hidden=False)
        data_pc1 = create_ho_data_from_factory(pc1)
        self.client.post('/create?type=1', data_pc1)
        # PL作成を確認
        pls = Player.objects.filter(engawa=gm.engawa, role=0)
        self.assertEqual(pls.count(), 1)
        pl1 = pls.first()
        # Auth作成を確認
        auths = Auth.objects.filter(player=pl1).order_by('id')
        self.assertEqual(auths.count(), 1)
        self.assertEqual(auths.first().auth_front, True)
        self.assertEqual(auths.first().auth_back, True)

        # HO1を作成
        ho1 = HandoutFactory.build(engawa=gm.engawa, hidden=False)
        data_ho1 = create_ho_data_from_factory(ho1)
        self.client.post('/create?type=3', data_ho1)
        # Auth作成を確認
        auths = Auth.objects.filter(player=pl1).order_by('id')
        self.assertEqual(auths.count(), 2)
        self.assertEqual(auths.all()[1].auth_front, True)
        self.assertEqual(auths.all()[1].auth_back, False)

        # PC2を作成
        pc2 = HandoutFactory.build(engawa=gm.engawa, hidden=False)
        data_pc2 = create_ho_data_from_factory(pc2)
        self.client.post('/create?type=1', data_pc2)
        # PL作成を確認
        pls = Player.objects.filter(engawa=gm.engawa, role=0).order_by('id')
        self.assertEqual(pls.count(), 2)
        pl2 = pls.last()
        # Auth作成を確認
        auths1 = Auth.objects.filter(player=pl1).order_by('id')
        auths2 = Auth.objects.filter(player=pl2).order_by('id')
        self.assertEqual(auths1.count(), 3)
        self.assertEqual(auths2.count(), 3)

        # NPC1を作成
        npc1 = HandoutFactory.build(engawa=gm.engawa, hidden=True)
        data_npc1 = create_ho_data_from_factory(npc1)
        self.client.post('/create?type=2', data_npc1)
        # Auth作成を確認
        auths1 = Auth.objects.filter(player=pl1).order_by('id')
        auths2 = Auth.objects.filter(player=pl2).order_by('id')
        self.assertEqual(auths1.count(), 4)
        self.assertEqual(auths2.count(), 4)
        self.assertEqual(auths1.last().auth_front, False)
        self.assertEqual(auths1.last().auth_back, False)
        self.assertEqual(auths2.last().auth_front, False)
        self.assertEqual(auths2.last().auth_back, False)

        # トータルのハンドアウト数を確認
        self.assertEqual(Handout.objects.filter(engawa=gm.engawa).count(), 4)

class HandoutDetailViewTest(TestCase):
    def test_ok_gm(self):
        """
        GMは公開，非公開ハンドアウトの秘密を見ることができる
        """
        # ログイン
        c = self.client
        gm = logined_user(c)
        c.get('/engawa')

        # 公開ハンドアウトの作成
        ho = HandoutFactory(engawa=gm.engawa, type=3, hidden=False)
        # 非公開ハンドアウトの作成
        npc = HandoutFactory(engawa=gm.engawa, type=2, hidden=True)
        # DB内にハンドアウトが2件存在することを確認
        self.assertEqual(Handout.objects.filter(engawa=gm.engawa).count(), 2)

        res1 = self.client.get(f'/detail/{ho.id}')
        self.assertTrue(res1.context['allowed'])
        self.assertEqual(res1.context['role_name'], 'GM')
        self.assertEqual(res1.context['ho_type'], 'HO')
        self.assertEqual(res1.context['handout'], ho)
        self.assertEqual(res1.status_code, 200)
        self.assertTemplateUsed(res1, 'homaster/detail.html')

        res2 = self.client.get(f'/detail/{npc.id}')
        self.assertTrue(res2.context['allowed'])
        self.assertEqual(res2.context['role_name'], 'GM')
        self.assertEqual(res2.context['ho_type'], 'NPC')
        self.assertEqual(res2.context['handout'], npc)
        self.assertEqual(res2.status_code, 200)
        self.assertTemplateUsed(res2, 'homaster/detail.html')

    def test_ok_pl(self):
        """
        PLは裏の閲覧権限のあるハンドアウトの秘密のみ見ることができる
        """
        # ログイン
        c = self.client
        pl = logined_user(c, 0)
        # PCに紐付くAuthの作成
        AuthFactory(player=pl, handout=pl.handout, auth_back=True)
        c.get('/engawa')

        # 公開ハンドアウトの作成
        ho = HandoutFactory(engawa=pl.engawa, type=3, hidden=False)
        # Authの作成
        AuthFactory(player=pl, handout=ho)
        # DB内にハンドアウトが2件存在することを確認
        self.assertEqual(Handout.objects.filter(engawa=pl.engawa).count(), 2)

        res1 = self.client.get(f'/detail/{pl.handout.id}')
        self.assertTrue(res1.context['allowed'])
        self.assertEqual(res1.context['role_name'], 'PC1')
        self.assertEqual(res1.context['ho_type'], 'PC')
        self.assertEqual(res1.context['handout'], pl.handout)
        self.assertEqual(res1.status_code, 200)
        self.assertTemplateUsed(res1, 'homaster/detail.html')

        res2 = self.client.get(f'/detail/{ho.id}')
        self.assertFalse(res2.context['allowed'])
        self.assertEqual(res2.context['role_name'], 'PC1')
        self.assertEqual(res2.context['ho_type'], 'HO')
        self.assertEqual(res2.context['handout'], ho)
        self.assertEqual(res2.status_code, 200)
        self.assertTemplateUsed(res2, 'homaster/detail.html')

    def test_get_ng_not_login(self):
        """
        ログインユーザでなければトップページにリダイレクトする
        """
        res = self.client.get('/detail/1')
        self.assertRedirects(res, '/index')

    def test_get_ng_without_pk(self):
        """
        URLにpkが含まれていなければトップページにリダイレクトする
        """
        # p_codeがないエラーログを無視
        with self.assertLogs('homaster.views', level='ERROR'):
            res = self.client.get('/detail')
        self.assertRedirects(res, '/index')

    def test_get_404_no_ho(self):
        """
        ログイン中のENGAWAにid=pkのハンドアウトがなければ404エラー
        """
        # ログイン
        c = self.client
        logined_user(c)
        c.get('/engawa')

        # 他所のENGAWAにハンドアウトを作成
        HandoutFactory()
        # ID=1のハンドアウトが存在することを確認
        self.assertTrue(Handout.objects.get(id=1))

        res = self.client.get('/detail/1')
        self.assertEqual(res.status_code, 404)

    def test_get_404_not_allowed(self):
        """
        ハンドアウトが非公開且つユーザがPLの場合，表の閲覧権限がなければ404
        """
        # ログイン
        c = self.client
        pl = logined_user(c, 0)
        c.get('/engawa')
        # 非公開ハンドアウトの作成
        npc = HandoutFactory(engawa=pl.engawa, type=2, hidden=True)
        # 非公開ハンドアウトに対するPCのAuthを作成
        AuthFactory(player=pl, handout=npc, auth_front=False)
        # ID=2のハンドアウトが存在することを確認
        self.assertTrue(Handout.objects.get(id=2))
        self.assertEqual(Handout.objects.get(id=2).type, 2)

        res = self.client.get('/detail/2')
        self.assertEqual(res.status_code, 404)

class UpdateHandoutViewTest(TestCase):
    def test_get_ok_gm(self):
        """
        GMがハンドアウト更新画面に遷移できる
        """
        # ログイン
        c = self.client
        gm = logined_user(c)
        c.get('/engawa')

        # 公開ハンドアウトの作成
        ho = HandoutFactory(engawa=gm.engawa, type=3, hidden=False)
        # DB内にハンドアウトが1件存在することを確認
        self.assertEqual(Handout.objects.filter(engawa=gm.engawa).count(), 1)

        res = self.client.get(f'/update/{ho.id}')
        self.assertEqual(res.context['role_name'], 'GM')
        self.assertEqual(res.context['ho_type'], 'HO')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'homaster/update.html')

    def test_form_valid(self):
        """
        ハンドアウトが更新されること。
        hiddenの変更によって紐付くAuthが更新されること
        2021年10月現在，セッション開始後のhidden変更はないものとする。

        シナリオ：
        PC1とHO1（公開）を作成した後，HO1の全カラムを更新した上で非公開にする
        用意するもの：
        PC1，それに紐づくPLとAuth
        HO1，それに紐づくPLのAuth
        """
        # ログイン
        c = self.client
        gm = logined_user(c)
        c.get('/engawa')

        # PC1とそれに紐づくPLとAuthを作成
        pc1 = HandoutFactory(engawa=gm.engawa, hidden=False)
        pl = PlayerFactory(email=None, engawa=gm.engawa, handout=pc1)
        auth1 = AuthFactory(player=pl, handout=pc1, auth_back=True)

        # HO1とそれに紐づくPLのAuth
        ho1 = HandoutFactory(engawa=gm.engawa, hidden=False, type=3)
        auth2 = AuthFactory(player=pl, handout=ho1)

        ho1_2 = HandoutFactory.build(engawa=gm.engawa, hidden=True, type=3)
        self.assertNotEqual(ho1_2.pc_name, ho1.pc_name)
        data_ho1_2 = create_ho_data_from_factory(ho1_2)
        res = self.client.post(f'/update/{ho1.id}', data_ho1_2)
        self.assertRedirects(res, '/engawa')

        # 更新後のHO1を取得
        ho_after = Handout.objects.get(id=ho1.id)
        self.assertTrue(ho_after.hidden)
        self.assertEqual(ho_after.pc_name, ho1_2.pc_name)
        self.assertEqual(ho_after.pl_name, ho1_2.pl_name)
        self.assertEqual(ho_after.front, ho1_2.front)
        self.assertEqual(ho_after.back, ho1_2.back)

        # Auth更新を確認
        auth1_2 = Auth.objects.get(id=auth1.id)
        auth2_2 = Auth.objects.get(id=auth2.id)
        self.assertTrue(auth1_2.auth_front)
        self.assertFalse(auth2_2.auth_front)

    def test_get_ng_not_login(self):
        """
        ログインユーザでなければトップページにリダイレクトする
        """
        res = self.client.get("/update/1")
        self.assertRedirects(res, '/index')

    def test_get_ng_not_gm(self):
        """
        ログイン済でもGMでなければ404エラーを返す
        """
        pl = logined_user(self.client, 0)
        with self.assertLogs('homaster.views', level='ERROR') as cm:
            res = self.client.get("/update/1")
        err = f"This player with p_code {pl.p_code} is not GM."
        self.assertIn(err, cm.output[0])
        self.assertEqual(res.status_code, 404)

    def test_get_404_no_ho(self):
        """
        ログイン中のENGAWAにid=pkのハンドアウトがなければ404エラー
        """
        # ログイン
        c = self.client
        logined_user(c)
        c.get('/engawa')

        # 他所のENGAWAにハンドアウトを作成
        HandoutFactory()
        # ID=1のハンドアウトが存在することを確認
        self.assertTrue(Handout.objects.get(id=1))

        res = self.client.get('/update/1')
        self.assertEqual(res.status_code, 404)

class ConfirmCloseViewTest(TestCase):
    def test_get_ok(self):
        """
        GMがENGAWAクローズ確認モーダルを表示できる
        """
        # ログイン
        c = self.client
        logined_user(c)
        c.get('/engawa')

        res = c.get('/close-engawa')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'homaster/close_confirm_modal.html')
        self.assertTrue(res.context['submit_token'])

    def test_post_ok(self):
        """
        ENGAWAクローズ確認モーダルでSubmitすると，
        最終的にクローズ完了画面に遷移する
        """
        # ログイン
        c = self.client
        logined_user(c)
        c.get('/engawa')

        res = c.post('/close-engawa')
        self.assertRedirects(res, '/close-success')

class HandoutTypeChoiceViewTest(TestCase):
    def test_get_ok(self):
        """
        GMがハンドアウト種別選択モーダルを表示できる
        """
        # ログイン
        c = self.client
        logined_user(c)
        c.get('/engawa')

        res = c.get('/create-handout')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'homaster/type_choice_modal.html')

    def test_post_ok(self):
        """
        ハンドアウト種別選択モーダルでSubmitすると，
        ハンドアウト作成画面に遷移する
        """
        # ログイン
        c = self.client
        logined_user(c)
        c.get('/engawa')

        res = c.post('/create-handout', {"type": 1})
        self.assertRedirects(res, '/create?type=1')

class AuthControlViewTest(TestCase):
    def test_get_ok(self):
        """
        GM, PLが閲覧権限更新モーダルを表示できる
        PC1: PC2 ○, PC3 x
        PC2: PC1 ○, PC3 x
        PC3: PC1 x, PC2 x
        NPC1(公開): PC1 裏○, PC2 裏x, PC3 裏○
        HO1(非公開): PC1 x, PC2 表○, PC3 裏○

        PLの場合は1行のみ, チェックボックスが無効なことも確認。
        """
        # ログイン
        c = self.client
        gm = logined_user(c)

        # PC1とそれに紐づくPLとAuthを作成
        pc1 = HandoutFactory(engawa=gm.engawa, hidden=False)
        pl1 = PlayerFactory(email=None, engawa=gm.engawa, handout=pc1, role=0)
        auth_pl1_pc1 = AuthFactory(player=pl1, handout=pc1, auth_back=True)

        # PC2とそれに紐づくPLとAuthを作成
        pc2 = HandoutFactory(engawa=gm.engawa, hidden=False)
        pl2 = PlayerFactory(email=None, engawa=gm.engawa, handout=pc2, role=0)
        auth_pl2_pc1 = AuthFactory(player=pl2, handout=pc2, auth_back=True)
        auth_pl1_pc2 = AuthFactory(player=pl1, handout=pc2, auth_back=True)
        auth_pl2_pc2 = AuthFactory(player=pl2, handout=pc1, auth_back=True)

        # PC3とそれに紐づくPLとAuthを作成
        pc3 = HandoutFactory(engawa=gm.engawa, hidden=False)
        pl3 = PlayerFactory(email=None, engawa=gm.engawa, handout=pc3, role=0)
        auth_pl3_pc1 = AuthFactory(player=pl3, handout=pc1, auth_back=False)
        auth_pl3_pc2 = AuthFactory(player=pl3, handout=pc2, auth_back=False)
        auth_pl3_pc3 = AuthFactory(player=pl3, handout=pc3, auth_back=True)
        auth_pl1_pc3 = AuthFactory(player=pl1, handout=pc3, auth_back=False)
        auth_pl2_pc3 = AuthFactory(player=pl2, handout=pc3, auth_back=False)

        # NPC1とそれに紐づくPLのAuth
        npc1 = HandoutFactory(engawa=gm.engawa, hidden=False, type=2)
        auth_pl1_npc1 = AuthFactory(player=pl1, handout=npc1, auth_back=True)
        auth_pl2_npc1 = AuthFactory(player=pl2, handout=npc1)
        auth_pl3_npc1 = AuthFactory(player=pl3, handout=npc1, auth_back=True)

        # HO1とそれに紐づくPLのAuth
        ho1 = HandoutFactory(engawa=gm.engawa, hidden=True, type=3)
        auth_pl1_ho1 = AuthFactory(player=pl1, handout=ho1, auth_front=False)
        auth_pl2_ho1 = AuthFactory(player=pl2, handout=ho1)
        auth_pl3_ho1 = AuthFactory(player=pl3, handout=ho1, auth_back=True)

        # 管理画面リロード
        c.get('/engawa')

        # モーダル表示
        res1 = c.get('/auth-control')
        self.assertEqual(res1.status_code, 200)

        # context確認
        self.assertEqual(
            res1.context['ho_names'],
            ['PC1', 'PC2', 'PC3', 'NPC1', 'HO1'])
        
        choices_PC1 = [
            (str(auth_pl1_pc1.id), ''),
            (str(auth_pl1_pc2.id), ''),
            (str(auth_pl1_pc3.id), ''),
            (str(auth_pl1_npc1.id), ''),
            (str(auth_pl1_ho1.id), ''),
        ]
        choices_PC2 = [
            (str(auth_pl2_pc1.id), ''),
            (str(auth_pl2_pc2.id), ''),
            (str(auth_pl2_pc3.id), ''),
            (str(auth_pl2_npc1.id), ''),
            (str(auth_pl2_ho1.id), ''),
        ]
        choices_PC3 = [
            (str(auth_pl3_pc1.id), ''),
            (str(auth_pl3_pc2.id), ''),
            (str(auth_pl3_pc3.id), ''),
            (str(auth_pl3_npc1.id), ''),
            (str(auth_pl3_ho1.id), ''),
        ]

        # 選択肢，初期値の確認
        # 選択肢は表裏で同じなので表だけ確認する
        # PC1
        self.assertEqual(
            res1.context['form'].fields['PC1_front'].choices,
            choices_PC1)
        self.assertEqual(
            res1.context['form'].fields['PC1_front'].initial,
            [auth_pl1_pc1.id, auth_pl1_pc2.id, auth_pl1_pc3.id, auth_pl1_npc1.id])
        self.assertEqual(
            res1.context['form'].fields['PC1_back'].initial,
            [auth_pl1_pc1.id, auth_pl1_pc2.id, auth_pl1_npc1.id])

        # PC2
        self.assertEqual(
            res1.context['form'].fields['PC2_front'].choices,
            choices_PC2)
        self.assertEqual(
            res1.context['form'].fields['PC2_front'].initial,
            [auth_pl2_pc1.id, auth_pl2_pc2.id, auth_pl2_pc3.id, auth_pl2_npc1.id, auth_pl2_ho1.id])
        self.assertEqual(
            res1.context['form'].fields['PC2_back'].initial,
            [auth_pl2_pc1.id, auth_pl2_pc2.id])

        # PC3
        self.assertEqual(
            res1.context['form'].fields['PC3_front'].choices,
            choices_PC3)
        self.assertEqual(
            res1.context['form'].fields['PC3_front'].initial,
            [auth_pl3_pc1.id, auth_pl3_pc2.id, auth_pl3_pc3.id, auth_pl3_npc1.id, auth_pl3_ho1.id])
        self.assertEqual(
            res1.context['form'].fields['PC3_back'].initial,
            [auth_pl3_pc3.id, auth_pl3_npc1.id, auth_pl3_ho1.id])

        # PL(PC1)テスト
        url_pc1 = f'/{gm.engawa.uuid}?p_code={pc1.p_code}'
        # PC1でログイン
        res2 = c.get(url_pc1)
        self.assertRedirects(res2, '/engawa')
        # モーダルを開く
        res3 = c.get('/auth-control')
        self.assertEqual(res3.status_code, 200)
        # 選択肢，初期値，disabledの確認
        self.assertEqual(
            res3.context['form'].fields['PC1_front'].choices,
            choices_PC1)
        self.assertEqual(
            res3.context['form'].fields['PC1_front'].initial,
            [auth_pl1_pc1.id, auth_pl1_pc2.id, auth_pl1_pc3.id, auth_pl1_npc1.id])
        self.assertEqual(
            res3.context['form'].fields['PC1_back'].initial,
            [auth_pl1_pc1.id, auth_pl1_pc2.id, auth_pl1_npc1.id])
        self.assertTrue(res3.context['form'].fields['PC1_front'].disabled)
        self.assertTrue(res3.context['form'].fields['PC1_back'].disabled)

    def test_post_ok(self):
        """
        閲覧権限を更新できる
        裏を更新，表を更新，両方更新，更新しない
        """

        # ログイン
        c = self.client
        gm = logined_user(c)

        # PC1とそれに紐づくPLとAuthを作成
        pc1 = HandoutFactory(engawa=gm.engawa, hidden=False)
        pl1 = PlayerFactory(email=None, engawa=gm.engawa, handout=pc1, role=0)
        auth_pl1_pc1 = AuthFactory(player=pl1, handout=pc1, auth_back=True)

        # HO1とそれに紐づくPLのAuth
        ho1 = HandoutFactory(engawa=gm.engawa, hidden=True, type=3)
        auth_pl1_ho1 = AuthFactory(player=pl1, handout=ho1, auth_front=False)

        # 管理画面リロード
        c.get('/engawa')

        set_submit_token(c)
        data1 = {
            "submit_token": "test",
            "PC1_front": [f"{auth_pl1_pc1.id}", f"{auth_pl1_ho1.id}"]
        }
        res1 = c.post(f'/auth-control', data1)
        self.assertEqual(res1.json(), {'__all__': None})
        self.assertTrue(Auth.objects.get(id=auth_pl1_ho1.id).orig_auth['auth_front'])
        self.assertFalse(Auth.objects.get(id=auth_pl1_ho1.id).orig_auth['auth_back'])

        set_submit_token(c)
        data2 = {
            "submit_token": "test",
            "PC1_front": [f"{auth_pl1_pc1.id}", f"{auth_pl1_ho1.id}"],
            "PC1_back": [f"{auth_pl1_pc1.id}", f"{auth_pl1_ho1.id}"]
        }
        res2 = c.post(f'/auth-control', data2)
        self.assertEqual(res2.json(), {'__all__': None})
        self.assertTrue(Auth.objects.get(id=auth_pl1_ho1.id).orig_auth['auth_front'])
        self.assertTrue(Auth.objects.get(id=auth_pl1_ho1.id).orig_auth['auth_back'])

        set_submit_token(c)
        data3 = {
            "submit_token": "test",
            "PC1_front": [f"{auth_pl1_pc1.id}"],
            "PC1_back": [f"{auth_pl1_pc1.id}"]
        }
        res3 = c.post(f'/auth-control', data3)
        self.assertEqual(res3.json(), {'__all__': None})
        self.assertFalse(Auth.objects.get(id=auth_pl1_ho1.id).orig_auth['auth_front'])
        self.assertFalse(Auth.objects.get(id=auth_pl1_ho1.id).orig_auth['auth_back'])

    def test_post_ng_without_token(self):
        """
        POSTデータとセッションにsubmit_tokenが含まれなければ，
        DBを更新しない
        """
        # ログイン
        c = self.client
        gm = logined_user(c)

        # PC1とそれに紐づくPLとAuthを作成
        pc1 = HandoutFactory(engawa=gm.engawa, hidden=False)
        pl1 = PlayerFactory(email=None, engawa=gm.engawa, handout=pc1, role=0)
        auth_pl1_pc1 = AuthFactory(player=pl1, handout=pc1, auth_back=True)

        # HO1とそれに紐づくPLのAuth
        ho1 = HandoutFactory(engawa=gm.engawa, hidden=True, type=3)
        auth_pl1_ho1 = AuthFactory(player=pl1, handout=ho1, auth_front=False)

        # 管理画面リロード
        c.get('/engawa')

        data = {
            "submit_token": "test",
            "PC1_front": [f"{auth_pl1_pc1.id}", f"{auth_pl1_ho1.id}"],
            "PC1_back": [f"{auth_pl1_pc1.id}", f"{auth_pl1_ho1.id}"]
        }
        res = c.post(f'/auth-control', data)
        self.assertRedirects(res, '/engawa')
        self.assertFalse(Auth.objects.get(id=auth_pl1_ho1.id).orig_auth['auth_front'])
        self.assertFalse(Auth.objects.get(id=auth_pl1_ho1.id).orig_auth['auth_back'])

class InvitelViewTest(TestCase):
    def test_get_ok(self):
        """
        PLの招待URLを取得できる
        pl_nameが空の場合は「匿名プレイヤー」が入る
        """
        # ログイン
        c = self.client
        gm = logined_user(c)

        # PC1を作成
        pc1 = HandoutFactory(engawa=gm.engawa, hidden=False)
        pl1 = PlayerFactory(email=None, engawa=gm.engawa, handout=pc1)

        # PC2を作成
        pc2 = HandoutFactory(engawa=gm.engawa, hidden=False, pl_name="")
        pl2 = PlayerFactory(email=None, engawa=gm.engawa, handout=pc2)

        # 管理画面リロード
        c.get('/engawa')

        data = [
            (pc1.pl_name, f'https://testserver/{gm.engawa.uuid}?p_code={pc1.p_code}', 'PC1'),
            ('匿名プレイヤー', f'https://testserver/{gm.engawa.uuid}?p_code={pc2.p_code}', 'PC2'),
            ('GM', f'https://testserver/{gm.engawa.uuid}?p_code={gm.p_code}', 'GM')
        ]

        res1 = c.get(f'/invite', HTTP_HOST='testserver')
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.context['handouts'], data)

class ConfirmDeleteViewTest(TestCase):
    def test_get_ok(self):
        """
        ハンドアウト削除確認画面を表示できる
        """
        # ログイン
        c = self.client
        gm = logined_user(c)

        # PC1を作成
        pc1 = HandoutFactory(engawa=gm.engawa, hidden=False)

        res = c.get(f'/delete-handout?id={pc1.id}&name=PC1')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['handout'], pc1)
        self.assertEqual(res.context['ho_name'], "PC1")
        self.assertTrue(res.context['submit_token'])

    def test_post_ok(self):
        # ログイン
        c = self.client
        gm = logined_user(c)

        # PC1を作成
        pc1 = HandoutFactory(engawa=gm.engawa, hidden=False)

        c.get(f'/delete-handout?id={pc1.id}&name=PC1')

        set_submit_token(c)

        res = c.post(f'/delete-handout?id={pc1.id}&name=PC1', {"submit_token": "test"})
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, f'/delete?id={pc1.id}', target_status_code=302)

def logined_user(client, role=1):
    """
    ログイン済のPlayerを返す
    """
    if role == 1:
        pl = PlayerFactory(engawa=EngawaFactory(), handout=None, p_code='testgm01')
    else:
        gm = PlayerFactory(engawa=EngawaFactory(), handout=None, p_code='testgm01')
        ho = HandoutFactory(engawa=gm.engawa)
        pl = PlayerFactory(engawa=gm.engawa, handout=ho, email=None, role=role)
    e_uuid = pl.engawa.uuid
    p_code = pl.p_code
    url = f'/{e_uuid}?p_code={p_code}'
    # ログイン
    client.get(url)
    return pl

def create_ho_data_from_factory(factory):
    return {
        'hidden': factory.hidden,
        'pc_name': factory.pc_name,
        'pl_name': factory.pl_name,
        'front': factory.front,
        'back': factory.back
    }

def set_submit_token(c):
    s = c.session
    s.update({'submit_token': 'test'})
    s.save()
