import pygame
import sys
import random
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator


# --- OYUN YÖNETİCİSİ (ÇEKİRDEK MOTOR) ---
class GameManager:
    def __init__(self, board_size=8):
        self.board_size = board_size
        self.backend_tipi = "simülatör"
        self.simulator = AerSimulator()
        self.ibm_backend = None
        self.ships = {}
        self.vurulan_kareler = set()
        self.gemi_sayaci = 1

    def ibm_baglantisi_kur(self, api_key):
        try:
            from qiskit_ibm_runtime import QiskitRuntimeService
            QiskitRuntimeService.save_account(channel="ibm_quantum", token=api_key, overwrite=True)
            service = QiskitRuntimeService(channel="ibm_quantum")
            self.ibm_backend = service.least_busy(operational=True, simulator=False)
            self.backend_tipi = "ibm"
            return True, self.ibm_backend.name
        except ImportError:
            return False, "'qiskit-ibm-runtime' kütüphanesi eksik!"
        except Exception as e:
            return False, str(e)

    def gemi_yerlestir_klasik(self, x, y):
        isim = f"Klasik_{self.gemi_sayaci}"
        self.ships[isim] = {'tip': 'klasik', 'koordinatlar': [(x, y)], 'durum': 'aktif'}
        self.gemi_sayaci += 1

    def gemi_yerlestir_hayalet(self, koord1, koord2):
        isim = f"Hayalet_{self.gemi_sayaci}"
        self.ships[isim] = {'tip': 'hayalet', 'koordinatlar': [koord1, koord2], 'durum': 'aktif'}
        self.gemi_sayaci += 1

    def gemi_yerlestir_hileli(self, koord1, koord2, agirlik=0.75):
        isim = f"Hileli_{self.gemi_sayaci}"
        theta = 2 * np.arccos(np.sqrt(agirlik))
        self.ships[isim] = {'tip': 'hileli', 'koordinatlar': [koord1, koord2], 'theta': theta, 'agirlik': agirlik,
                            'durum': 'aktif'}
        self.gemi_sayaci += 1

    def qc_hedef_belirle(self):
        olasi_hedefler = [(x, y) for x in range(self.board_size) for y in range(self.board_size) if
                          (x, y) not in self.vurulan_kareler]
        if not olasi_hedefler: return None
        hedef = random.choice(olasi_hedefler)
        self.vurulan_kareler.add(hedef)
        return hedef

    def atis_cozumle(self, hedef):
        for isim, veri in self.ships.items():
            if veri['durum'] != 'aktif': continue
            if hedef in veri['koordinatlar']:
                if veri['tip'] == 'klasik':
                    veri['durum'] = 'batti'
                    return 'batti_klasik'
                elif veri['tip'] in ['hayalet', 'hileli']:
                    return self._kuantum_cokme_hesapla(isim, veri, hedef)
        return 'karavana'

    def _kuantum_cokme_hesapla(self, isim, veri, atis_hedefi):
        qc = QuantumCircuit(1, 1)
        if veri['tip'] == 'hayalet':
            qc.h(0)
        elif veri['tip'] == 'hileli':
            qc.ry(veri['theta'], 0)
        qc.measure(0, 0)

        if self.backend_tipi == "ibm" and self.ibm_backend:
            transpiled_qc = transpile(qc, self.ibm_backend)
            job = self.ibm_backend.run(transpiled_qc, shots=1)
            result = job.result()
        else:
            result = self.simulator.run(qc, shots=1).result()

        coken_durum = list(result.get_counts().keys())[0]
        gercek_konum = veri['koordinatlar'][int(coken_durum)]

        if gercek_konum == atis_hedefi:
            veri['durum'] = 'batti'
            veri['koordinatlar'] = [gercek_konum]
            return 'batti_kuantum'
        else:
            veri['tip'] = 'klasik'
            veri['koordinatlar'] = [gercek_konum]
            return 'kurtuldu_kuantum'


# --- API KEY GİRİŞ EKRANI ---
def api_key_ekrani_goster(ekran, font_buyuk, font_kucuk, saat):
    W, H = ekran.get_size()
    giriş_metin = ""
    aktif = True
    hata_mesaj = ""

    R_BG = (4, 8, 12)
    R_CYAN = (0, 210, 255)
    R_GOLD = (255, 200, 50)
    R_DIM = (130, 160, 190)
    R_WHITE = (240, 248, 255)
    R_RED = (255, 80, 80)

    # Yanıp sönen imleç
    imlek_visible = True
    imlek_timer = 0

    while aktif:
        dt = saat.tick(60)
        imlek_timer += dt
        if imlek_timer > 500:
            imlek_visible = not imlek_visible
            imlek_timer = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None  # İptal
                elif event.key == pygame.K_RETURN:
                    if len(giriş_metin) > 10:
                        return giriş_metin
                    else:
                        hata_mesaj = "API KEY ÇOK KISA!"
                elif event.key == pygame.K_BACKSPACE:
                    giriş_metin = giriş_metin[:-1]
                    hata_mesaj = ""
                else:
                    if len(giriş_metin) < 80:
                        giriş_metin += event.unicode

        ekran.fill(R_BG)

        # Dekoratif çizgiler
        for i in range(0, W, 40):
            pygame.draw.line(ekran, (10, 20, 30), (i, 0), (i, H), 1)
        for i in range(0, H, 40):
            pygame.draw.line(ekran, (10, 20, 30), (0, i), (W, i), 1)

        # Başlık
        baslik = font_buyuk.render("IBM QUANTUM API ANAHTARI", True, R_CYAN)
        ekran.blit(baslik, baslik.get_rect(center=(W // 2, 100)))

        alt = font_kucuk.render("IBM Quantum hesabınızdan API key'inizi girin", True, R_DIM)
        ekran.blit(alt, alt.get_rect(center=(W // 2, 140)))

        # Input kutusu
        kutu = pygame.Rect(40, H // 2 - 30, W - 80, 60)
        pygame.draw.rect(ekran, (8, 20, 35), kutu)
        pygame.draw.rect(ekran, R_CYAN, kutu, 2)

        # Maskelenmiş metin (güvenlik için yıldız)
        gosterim = "*" * len(giriş_metin)
        if imlek_visible:
            gosterim += "|"
        metin_surf = font_kucuk.render(gosterim if gosterim else "Key'inizi buraya yazın...", True,
                                       R_WHITE if giriş_metin else R_DIM)
        ekran.blit(metin_surf, (kutu.x + 15, kutu.y + 18))

        # Alt bilgi
        if hata_mesaj:
            hata = font_kucuk.render(hata_mesaj, True, R_RED)
            ekran.blit(hata, hata.get_rect(center=(W // 2, H // 2 + 60)))
        else:
            bilgi1 = font_kucuk.render("[ENTER] Onayla    [ESC] İptal / Simülatöre dön", True, R_DIM)
            ekran.blit(bilgi1, bilgi1.get_rect(center=(W // 2, H // 2 + 65)))

        uyari = font_kucuk.render("⚠  IBM QPU kuyruğu saatler sürebilir. Oyun yanıt vermez görünebilir.", True, R_GOLD)
        ekran.blit(uyari, uyari.get_rect(center=(W // 2, H - 80)))

        pygame.display.flip()

    return None


# --- ARAYÜZ ---
def oyunu_baslat():
    pygame.init()

    HUCRE = 80
    BOARD_SIZE = 8
    HUD_YUKSEKLIK = 120

    GERCEK_EKRAN = pygame.display.set_mode((BOARD_SIZE * HUCRE, BOARD_SIZE * HUCRE + HUD_YUKSEKLIK))
    ekran = pygame.Surface((BOARD_SIZE * HUCRE, BOARD_SIZE * HUCRE + HUD_YUKSEKLIK))
    pygame.display.set_caption("⚛  Kuantum Amiral Battı  —  QCAB v6.0")

    # --- FONT---
    try:
        font_buyuk = pygame.font.SysFont("Courier New", 26, bold=True)
        font_kucuk = pygame.font.SysFont("Courier New", 17, bold=True)
        font_mikro = pygame.font.SysFont("Courier New", 14)
    except:
        font_buyuk = pygame.font.SysFont("Consolas", 26, bold=True)
        font_kucuk = pygame.font.SysFont("Consolas", 17, bold=True)
        font_mikro = pygame.font.SysFont("Consolas", 14)

    # --- RENK PALETİ  ---
    R_BG       = (4, 8, 14)           # Koyu lacivert-siyah
    R_HUD_BG   = (6, 12, 20)          # HUD arka planı
    R_GRID     = (18, 35, 55)         # Izgara çizgileri
    R_GRID_DIM = (10, 22, 38)         # Izgara hücre arka planı
    R_CYAN     = (0, 220, 255)        # Vurgu - Hayalet / Aktif
    R_GOLD     = (255, 200, 50)       # Vurgu - Hedef / Tur
    R_GREEN    = (0, 255, 140)        # Başarı / Metin
    R_RED      = (255, 70, 70)        # Tehlike / Batma
    R_PURPLE   = (180, 60, 255)       # Hileli gemi
    R_WHITE    = (240, 248, 255)      # Normal yazı
    R_DIM      = (120, 155, 185)      # Soluk / yardımcı
    R_KLASIK   = (80, 110, 145)       # Klasik gemi rengi
    R_HIT_BG   = (25, 15, 10)        # Vurulmuş kare arkaplanı

    oyun = GameManager(BOARD_SIZE)
    saat = pygame.time.Clock()

    MAX_TUR = 30
    envanter = {"klasik": 3, "hayalet": 2, "hileli": 1}
    faz = "ANA_MENU"
    secili_tip = "klasik"
    gecici_koordinatlar = []
    animasyon_hedefi = None
    animasyon_baslangic = 0
    titreme_miktari = 0
    parcaciklar = []
    radar_halkalari = []
    mesaj = "SİSTEM HAZIR."

    # --- HUD'a sabit açıklama metni ---
    _hud_alt_mesaj = ""

    def vfx_patlama_olustur(x, y, renk, adet=35):
        for _ in range(adet):
            px = x * HUCRE + HUCRE // 2
            py = y * HUCRE + HUD_YUKSEKLIK + HUCRE // 2
            hiz = random.uniform(1.5, 6)
            aci = random.uniform(0, 2 * np.pi)
            vx, vy = np.cos(aci) * hiz, np.sin(aci) * hiz
            omur = random.randint(25, 50)
            boyut = random.randint(2, 5)
            parcaciklar.append([px, py, vx, vy, omur, renk, boyut])

    def ciz_izgara_hucre(surf, x, y, renk_ic=None, renk_kenar=None):
        rect = pygame.Rect(x * HUCRE, y * HUCRE + HUD_YUKSEKLIK, HUCRE, HUCRE)
        if renk_ic:
            pygame.draw.rect(surf, renk_ic, rect)
        pygame.draw.rect(surf, renk_kenar or R_GRID, rect, 1)
        return rect

    def ciz_metin_golge(surf, font, metin, renk, pos, golge_renk=(0,0,0), ofset=2):
        g = font.render(metin, True, golge_renk)
        surf.blit(g, (pos[0] + ofset, pos[1] + ofset))
        t = font.render(metin, True, renk)
        surf.blit(t, pos)

    # --- HUD çizim yardımcısı ---
    def ciz_hud_sınır(surf):
        # Alt kenar çizgisi - parlak çift çizgi efekti
        pygame.draw.line(surf, R_DIM, (0, HUD_YUKSEKLIK - 2), (BOARD_SIZE * HUCRE, HUD_YUKSEKLIK - 2), 1)
        pygame.draw.line(surf, R_CYAN, (0, HUD_YUKSEKLIK - 1), (BOARD_SIZE * HUCRE, HUD_YUKSEKLIK - 1), 1)

    while True:
        simdiki_zaman = pygame.time.get_ticks()
        kalan_tur = MAX_TUR - len(oyun.vurulan_kareler)
        aktif_gemi_sayisi = sum(1 for v in oyun.ships.values() if v['durum'] == 'aktif')

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if faz == "ANA_MENU":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        faz = "YERLESTIRME"
                        mesaj = "SİMÜLATÖR AKTİF — FİLOYU KONUŞLANDIR"
                    elif event.key == pygame.K_2:
                        # Kullanıcıdan API key al
                        api_key = api_key_ekrani_goster(GERCEK_EKRAN, font_buyuk, font_kucuk, saat)
                        if api_key:
                            # Bağlantı ekranı göster
                            GERCEK_EKRAN.fill((4, 8, 14))
                            bekle_txt = font_buyuk.render("IBM QPU'YA BAĞLANIYOR...", True, R_GOLD)
                            GERCEK_EKRAN.blit(bekle_txt, bekle_txt.get_rect(center=(BOARD_SIZE * HUCRE // 2, (BOARD_SIZE * HUCRE + HUD_YUKSEKLIK) // 2)))
                            pygame.display.flip()

                            basarili, sonuc = oyun.ibm_baglantisi_kur(api_key)
                            if basarili:
                                mesaj = f"BAĞLANDI: {sonuc.upper()}"
                            else:
                                mesaj = f"HATA: {sonuc[:35]}... — SİMÜLATÖR AKTİF"
                        else:
                            mesaj = "İPTAL EDİLDİ — SİMÜLATÖR AKTİF"
                        faz = "YERLESTIRME"

            elif faz == "YERLESTIRME":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1: secili_tip = "klasik"
                    elif event.key == pygame.K_2: secili_tip = "hayalet"
                    elif event.key == pygame.K_3: secili_tip = "hileli"
                    elif event.key == pygame.K_RETURN and sum(envanter.values()) == 0:
                        faz, mesaj = "SAVUNMA", "SAVAŞ BAŞLADI! [BOŞLUK] İLE ATEŞ ET."

                elif event.type == pygame.MOUSEBUTTONDOWN and event.pos[1] > HUD_YUKSEKLIK:
                    x, y = event.pos[0] // HUCRE, (event.pos[1] - HUD_YUKSEKLIK) // HUCRE
                    if secili_tip == "klasik" and envanter["klasik"] > 0:
                        oyun.gemi_yerlestir_klasik(x, y); envanter["klasik"] -= 1
                    elif secili_tip in ["hayalet", "hileli"] and envanter[secili_tip] > 0:
                        gecici_koordinatlar.append((x, y))
                        if len(gecici_koordinatlar) == 2:
                            if secili_tip == "hayalet":
                                oyun.gemi_yerlestir_hayalet(gecici_koordinatlar[0], gecici_koordinatlar[1])
                            else:
                                oyun.gemi_yerlestir_hileli(gecici_koordinatlar[0], gecici_koordinatlar[1])
                            envanter[secili_tip] -= 1; gecici_koordinatlar.clear()
                    if sum(envanter.values()) == 0:
                        mesaj = "FİLO TAMAM! [ENTER] İLE SAVAŞI BAŞLAT."

            elif faz == "SAVUNMA":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    if kalan_tur > 0 and aktif_gemi_sayisi > 0:
                        hedef = oyun.qc_hedef_belirle()
                        if hedef:
                            animasyon_hedefi, animasyon_baslangic, faz = hedef, simdiki_zaman, "ANIMASYON"
                            mesaj = f"⚛  GÖZLEMLENECEK ALAN SEÇİLİYOR → {hedef}"
                            radar_halkalari.append([hedef[0] * HUCRE + HUCRE // 2,
                                                    hedef[1] * HUCRE + HUD_YUKSEKLIK + HUCRE // 2, 0])

        # Animasyon çözümleme
        if faz == "ANIMASYON" and simdiki_zaman - animasyon_baslangic > 1000:
            sonuc = oyun.atis_cozumle(animasyon_hedefi)
            faz, radar_halkalari = "SAVUNMA", []
            hx, hy = animasyon_hedefi
            if sonuc == 'batti_klasik':
                mesaj, titreme_miktari = "💥 KRİTİK HASAR! GEMİ BATTI.", 15
                vfx_patlama_olustur(hx, hy, R_RED)
            elif sonuc == 'batti_kuantum':
                mesaj, titreme_miktari = "⚛  DALGA ÇÖKTÜ — KUANTUM GEMİSİ BATTI!", 30
                vfx_patlama_olustur(hx, hy, R_CYAN, 50)
            elif sonuc == 'kurtuldu_kuantum':
                mesaj = "✦  MUCİZE! GEMİ SÜPERPOZİSYONDAN KAÇTI."
                vfx_patlama_olustur(hx, hy, R_GREEN, 20)
            else:
                mesaj = "~  KARAVANA. SİSTEM ISKALADI."
                vfx_patlama_olustur(hx, hy, R_DIM, 15)

            yeni_aktif = sum(1 for v in oyun.ships.values() if v['durum'] == 'aktif')
            if yeni_aktif == 0:
                faz, mesaj = "OYUN_BITTI", "■  SİSTEM KAZANDI. FİLO YOK EDİLDİ."
            elif len(oyun.vurulan_kareler) >= MAX_TUR:
                faz, mesaj = "OYUN_BITTI", "★  TEBRİKLER! 30 TUR DAYANDIN VE KAZANDIN!"

        # ====================== ÇİZİM ======================
        ekran.fill(R_BG)

        # Işık saçan ızgara arka planı
        for gx in range(BOARD_SIZE):
            for gy in range(BOARD_SIZE):
                r = pygame.Rect(gx * HUCRE, gy * HUCRE + HUD_YUKSEKLIK, HUCRE, HUCRE)
                pygame.draw.rect(ekran, R_GRID_DIM, r)
                pygame.draw.rect(ekran, R_GRID, r, 1)

        # Vurulmuş kareler
        for (vx, vy) in oyun.vurulan_kareler:
            r = pygame.Rect(vx * HUCRE, vy * HUCRE + HUD_YUKSEKLIK, HUCRE, HUCRE)
            pygame.draw.rect(ekran, R_HIT_BG, r)
            pygame.draw.rect(ekran, (35, 50, 70), r, 1)
            # X işareti
            m = r.center
            pygame.draw.line(ekran, (80, 40, 40), (m[0]-14, m[1]-14), (m[0]+14, m[1]+14), 2)
            pygame.draw.line(ekran, (80, 40, 40), (m[0]-14, m[1]+14), (m[0]+14, m[1]-14), 2)

        # Animasyon - yanıp sönen hedef
        if faz == "ANIMASYON" and animasyon_hedefi:
            ax, ay = animasyon_hedefi
            r = pygame.Rect(ax * HUCRE, ay * HUCRE + HUD_YUKSEKLIK, HUCRE, HUCRE)
            puls = abs(np.sin(simdiki_zaman * 0.008)) * 255
            surf_target = pygame.Surface((HUCRE, HUCRE), pygame.SRCALPHA)
            surf_target.fill((255, 200, 0, int(puls * 0.4)))
            ekran.blit(surf_target, r.topleft)
            pygame.draw.rect(ekran, R_GOLD, r, 2)

        # --- GEMİLER ---
        if faz != "ANA_MENU":
            for isim, v in oyun.ships.items():
                if v['durum'] == 'batti':
                    cx = v['koordinatlar'][0][0] * HUCRE + HUCRE // 2
                    cy = v['koordinatlar'][0][1] * HUCRE + HUD_YUKSEKLIK + HUCRE // 2
                    # Parlayan kırmızı daire
                    for r_off in range(3, 0, -1):
                        alpha_surf = pygame.Surface((HUCRE, HUCRE), pygame.SRCALPHA)
                        pygame.draw.circle(alpha_surf, (*R_RED, 60 // r_off),
                                           (HUCRE // 2, HUCRE // 2), HUCRE // 3 + r_off * 4)
                        ekran.blit(alpha_surf, (v['koordinatlar'][0][0] * HUCRE, v['koordinatlar'][0][1] * HUCRE + HUD_YUKSEKLIK))
                    pygame.draw.circle(ekran, R_RED, (cx, cy), HUCRE // 3)
                    pygame.draw.circle(ekran, (255, 150, 150), (cx, cy), HUCRE // 3, 2)
                else:
                    tip = v['tip']
                    renk = R_KLASIK if tip == 'klasik' else (R_CYAN if tip == 'hayalet' else R_PURPLE)
                    for (gx, gy) in v['koordinatlar']:
                        gemi_r = pygame.Rect(gx * HUCRE + 12, gy * HUCRE + HUD_YUKSEKLIK + 12, HUCRE - 24, HUCRE - 24)
                        if tip == 'klasik':
                            pygame.draw.rect(ekran, renk, gemi_r)
                            pygame.draw.rect(ekran, (130, 160, 195), gemi_r, 2)
                        else:
                            # Parlayan kenarlı kuantum gemisi
                            iç_r = gemi_r.inflate(-6, -6)
                            pygame.draw.rect(ekran, (*renk[:3], 30) if False else (renk[0]//6, renk[1]//6, renk[2]//6), gemi_r)
                            pygame.draw.rect(ekran, renk, gemi_r, 2)
                            pygame.draw.rect(ekran, (255, 255, 255), iç_r, 1)

                    # İki koordinatlı gemiler arası bağlantı çizgisi
                    if v['durum'] == 'aktif' and len(v['koordinatlar']) == 2:
                        p1 = (v['koordinatlar'][0][0] * HUCRE + HUCRE // 2,
                              v['koordinatlar'][0][1] * HUCRE + HUD_YUKSEKLIK + HUCRE // 2)
                        p2 = (v['koordinatlar'][1][0] * HUCRE + HUCRE // 2,
                              v['koordinatlar'][1][1] * HUCRE + HUD_YUKSEKLIK + HUCRE // 2)
                        pygame.draw.line(ekran, renk, p1, p2, 2)
                        # Ortada ⚛ sembolü
                        orta = ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)
                        sembol = font_mikro.render("⚛", True, renk)
                        ekran.blit(sembol, (orta[0] - sembol.get_width() // 2, orta[1] - sembol.get_height() // 2))

        # Yerleştirme çizgisi (önizleme)
        if faz == "YERLESTIRME" and len(gecici_koordinatlar) == 1:
            mx, my = pygame.mouse.get_pos()
            if my > HUD_YUKSEKLIK:
                renk_sec = R_CYAN if secili_tip == "hayalet" else R_PURPLE
                gx = gecici_koordinatlar[0][0] * HUCRE + HUCRE // 2
                gy = gecici_koordinatlar[0][1] * HUCRE + HUD_YUKSEKLIK + HUCRE // 2
                pygame.draw.line(ekran, renk_sec, (gx, gy), (mx, my), 2)

        # --- VFX ---
        for h in radar_halkalari:
            h[2] += 3
            alpha = max(0, 255 - int(h[2] * 4))
            surf_h = pygame.Surface((HUCRE * 2, HUCRE * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf_h, (*R_GOLD, alpha), (HUCRE, HUCRE), int(h[2]), 2)
            ekran.blit(surf_h, (h[0] - HUCRE, h[1] - HUCRE))
            if h[2] > HUCRE: h[2] = 0

        for p in parcaciklar[:]:
            p[0] += p[2]; p[1] += p[3]; p[4] -= 1
            alpha = max(0, int(p[4] / 50 * 255))
            pygame.draw.circle(ekran, p[5], (int(p[0]), int(p[1])), p[6])
            if p[4] <= 0: parcaciklar.remove(p)

        # ====================== HUD ======================
        pygame.draw.rect(ekran, R_HUD_BG, (0, 0, BOARD_SIZE * HUCRE, HUD_YUKSEKLIK))
        ciz_hud_sınır(ekran)

        # Motor durumu - sol üst köşe badge
        motor_txt = f"⚡ {oyun.backend_tipi.upper()}"
        motor_renk = R_GOLD if oyun.backend_tipi == "ibm" else R_GREEN
        motor_surf = font_mikro.render(motor_txt, True, motor_renk)
        pygame.draw.rect(ekran, (10, 25, 15) if oyun.backend_tipi != "ibm" else (25, 20, 5),
                         (4, 4, motor_surf.get_width() + 12, 20))
        ekran.blit(motor_surf, (10, 7))

        if faz == "ANA_MENU":
            # Başlık
            baslik = font_buyuk.render("KUANTUM AMİRAL BATTISI", True, R_CYAN)
            ekran.blit(baslik, baslik.get_rect(centerx=BOARD_SIZE * HUCRE // 2, y=10))

            s1 = font_kucuk.render("[1] YEREL SİMÜLATÖR  —  Hızlı, anlık", True, R_WHITE)
            s2 = font_kucuk.render("[2] IBM QUANTUM QPU  —  Gerçek, kuyruklı", True, R_GOLD)
            ekran.blit(s1, s1.get_rect(centerx=BOARD_SIZE * HUCRE // 2, y=50))
            ekran.blit(s2, s2.get_rect(centerx=BOARD_SIZE * HUCRE // 2, y=82))

        elif faz == "YERLESTIRME":
            # Tip seçici
            tipler = [("1", "KLASİK", R_KLASIK), ("2", "HAYALET", R_CYAN), ("3", "HİLELİ", R_PURPLE)]
            for i, (tus, ad, renk) in enumerate(tipler):
                aktif_sec = (secili_tip == ad.lower() or
                             (secili_tip == "klasik" and ad == "KLASİK") or
                             (secili_tip == "hayalet" and ad == "HAYALET") or
                             (secili_tip == "hileli" and ad == "HİLELİ"))
                tip_str = f"[{tus}] {ad}:{envanter[secili_tip if aktif_sec else ['klasik','hayalet','hileli'][i]]}"
                tip_str = f"[{tus}] {ad}:{list(envanter.values())[i]}"
                bg_renk = (*renk, 40) if False else renk
                if aktif_sec:
                    pygame.draw.rect(ekran, (renk[0]//5, renk[1]//5, renk[2]//5),
                                     (10 + i * 215, 8, 205, 30))
                    pygame.draw.rect(ekran, renk, (10 + i * 215, 8, 205, 30), 1)
                t = font_kucuk.render(tip_str, True, renk if aktif_sec else R_DIM)
                ekran.blit(t, (20 + i * 215, 12))

            durum_renk = R_GOLD if sum(envanter.values()) == 0 else R_WHITE
            durum_str = "FİLO TAMAM! [ENTER] İLE BAŞLAT." if sum(envanter.values()) == 0 else mesaj
            ciz_metin_golge(ekran, font_buyuk, durum_str, durum_renk, (10, 48))

            # Seçili tip ipucu
            ipucu = font_mikro.render(f"Seçili: {secili_tip.upper()} | {'Tek tık' if secili_tip == 'klasik' else 'İki kare seç'}", True, R_DIM)
            ekran.blit(ipucu, (10, 98))

        else:
            # Savaş HUD'u
            # Sol: Tur sayacı
            tur_str = f"TUR  {len(oyun.vurulan_kareler):02d} / {MAX_TUR}"
            tur_renk = R_RED if kalan_tur < 5 else (R_GOLD if kalan_tur < 10 else R_GREEN)
            ciz_metin_golge(ekran, font_buyuk, tur_str, tur_renk, (10, 15))

            # Sağ: Filo durumu
            gemi_str = f"GEMİ  {aktif_gemi_sayisi}"
            gemi_renk = R_RED if aktif_gemi_sayisi == 1 else R_WHITE
            gemi_surf = font_buyuk.render(gemi_str, True, gemi_renk)
            ekran.blit(gemi_surf, (BOARD_SIZE * HUCRE - gemi_surf.get_width() - 10, 15))

            # Orta: Mesaj
            mesaj_surf = font_kucuk.render(mesaj, True, R_WHITE)
            ekran.blit(mesaj_surf, mesaj_surf.get_rect(centerx=BOARD_SIZE * HUCRE // 2, y=50))

            # Alt: Talimat
            talimat = font_mikro.render("[BOŞLUK] → SİSTEM ATEŞ ETSİN", True, R_DIM)
            ekran.blit(talimat, talimat.get_rect(centerx=BOARD_SIZE * HUCRE // 2, y=96))

        # Oyun bitti overlay
        if faz == "OYUN_BITTI":
            overlay = pygame.Surface((BOARD_SIZE * HUCRE, BOARD_SIZE * HUCRE + HUD_YUKSEKLIK), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            ekran.blit(overlay, (0, 0))

            # Çerçeveli sonuç kutusu
            kutu_w, kutu_h = 500, 100
            kutu_x = (BOARD_SIZE * HUCRE - kutu_w) // 2
            kutu_y = (BOARD_SIZE * HUCRE + HUD_YUKSEKLIK) // 2 - kutu_h // 2
            pygame.draw.rect(ekran, (8, 18, 30), (kutu_x, kutu_y, kutu_w, kutu_h))
            pygame.draw.rect(ekran, R_CYAN, (kutu_x, kutu_y, kutu_w, kutu_h), 2)

            son_renk = R_RED if "SİSTEM" in mesaj else R_GOLD
            txt = font_buyuk.render(mesaj, True, son_renk)
            ekran.blit(txt, txt.get_rect(center=(BOARD_SIZE * HUCRE // 2, (BOARD_SIZE * HUCRE + HUD_YUKSEKLIK) // 2)))

        # Ekran titremesi
        sx = random.randint(-titreme_miktari, titreme_miktari) if titreme_miktari > 0 else 0
        sy = random.randint(-titreme_miktari, titreme_miktari) if titreme_miktari > 0 else 0
        if titreme_miktari > 0: titreme_miktari -= 1

        GERCEK_EKRAN.fill((0, 0, 0))
        GERCEK_EKRAN.blit(ekran, (sx, sy))
        pygame.display.flip()
        saat.tick(60)


if __name__ == "__main__":
    oyunu_baslat()