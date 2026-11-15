"""Tworzy dokumentację aktualnej aplikacji i przewodnik do wystąpienia.

Uruchamiać Pythonem z pakietem python-docx. Dane liczbowe pochodzą z zapisanych
raportów wskazanych poniżej, a nie z ponownego losowania eksperymentu.
"""
from pathlib import Path
import json
import shutil

from docx import Document
from docx.shared import Cm, Inches, Pt, RGBColor
from docx.enum.section import WD_SECTION_START, WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'dokumentacja' / 'aktualna'
ASSETS = OUT / 'materialy'
RACE_DIR = ROOT / 'wyniki/eksperymenty/race_20261115_173237_803615'
CLOSURE_DIR = ROOT / 'wyniki/eksperymenty/closure_20261115_173238_202521'
DATE = '15 listopada 2026'
RACE = json.loads((RACE_DIR / 'dane.json').read_text())
CLOSURE = json.loads((CLOSURE_DIR / 'dane.json').read_text())


def num(value, digits=1):
    return f'{value:.{digits}f}'.replace('.', ',')


def setup(doc):
    sec = doc.sections[0]
    portrait(sec)
    styles = doc.styles
    for name in ('Normal', 'Title', 'Subtitle', 'Heading 1', 'Heading 2', 'Heading 3', 'Caption'):
        st = styles[name]
        st.font.name = 'Arial'
        st.font.color.rgb = RGBColor(0, 0, 0)
        st._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'), 'Arial')
    normal = styles['Normal']
    normal.font.size = Pt(10.5)
    normal.paragraph_format.line_spacing = 1.1
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.widow_control = True
    for name, size, before, after in [('Title', 24, 0, 12), ('Subtitle', 12, 0, 8),
                                      ('Heading 1', 16, 0, 10), ('Heading 2', 12, 10, 5),
                                      ('Heading 3', 11, 8, 4)]:
        st = styles[name]
        st.font.size = Pt(size)
        st.font.bold = name != 'Subtitle'
        st.paragraph_format.space_before = Pt(before)
        st.paragraph_format.space_after = Pt(after)
        st.paragraph_format.keep_with_next = True
    styles['Caption'].font.size = Pt(9)
    styles['Caption'].font.bold = False
    styles['Caption'].font.italic = False
    styles['Caption'].paragraph_format.space_after = Pt(7)
    styles['Caption'].paragraph_format.line_spacing = 1.05
    for name in ('Title', 'Subtitle', 'Heading 1', 'Heading 2', 'Heading 3'):
        ppr = styles[name]._element.find(qn('w:pPr'))
        if ppr is not None:
            for border in list(ppr.findall(qn('w:pBdr'))):
                ppr.remove(border)
    f = sec.footer.paragraphs[0]
    f.alignment = WD_ALIGN_PARAGRAPH.CENTER
    field = OxmlElement('w:fldSimple')
    field.set(qn('w:instr'), 'PAGE')
    r = OxmlElement('w:r')
    t = OxmlElement('w:t')
    t.text = '1'
    r.append(t)
    field.append(r)
    f._p.append(field)
    for run in f.runs:
        run.font.size = Pt(9)
    doc.core_properties.author = ''
    doc.core_properties.subject = 'Laboratorium ACO dla problemu komiwojażera'


def portrait(sec):
    sec.orientation = WD_ORIENT.PORTRAIT
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.top_margin, sec.bottom_margin = Cm(1.9), Cm(1.8)
    sec.left_margin, sec.right_margin = Cm(2.1), Cm(2.1)
    sec.footer_distance = Cm(.7)


def landscape(sec):
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = Cm(29.7), Cm(21)
    sec.top_margin, sec.bottom_margin = Cm(1.4), Cm(1.5)
    sec.left_margin, sec.right_margin = Cm(1.5), Cm(1.5)
    sec.footer_distance = Cm(.6)


def page(doc, title, wide=False):
    desired = WD_ORIENT.LANDSCAPE if wide else WD_ORIENT.PORTRAIT
    if doc.sections[-1].orientation != desired:
        sec = doc.add_section(WD_SECTION_START.NEW_PAGE)
        (landscape if wide else portrait)(sec)
    else:
        doc.add_page_break()
    p = doc.add_paragraph(title, 'Heading 1')
    if wide:
        p.paragraph_format.space_after = Pt(4)
        for r in p.runs:
            r.font.size = Pt(14)
    return p


def para(doc, text='', *, bold=False, size=None):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = bold
    if size:
        r.font.size = Pt(size)
    return p


def h2(doc, text):
    return doc.add_paragraph(text, 'Heading 2')


def bullets(doc, texts):
    for text in texts:
        p = doc.add_paragraph(style='List Bullet')
        p.add_run(text)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.08


def code(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(7)
    r = p.add_run(text)
    r.font.name = 'Courier New'
    r.font.size = Pt(9)
    return p


def table(doc, headers, rows, widths, size=9.5, numeric=()):
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for col, width in zip(t.columns, widths):
        col.width = Cm(width)
    for c, text, width in zip(t.rows[0].cells, headers, widths):
        c.width = Cm(width)
        c.text = str(text)
    for row in rows:
        cells = t.add_row().cells
        for c, text, width in zip(cells, row, widths):
            c.width = Cm(width)
            c.text = str(text)
    tbl_pr = t._tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for name in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        edge = OxmlElement(f'w:{name}')
        for k, v in [('val', 'single'), ('sz', '5'), ('color', 'D9D9D9')]:
            edge.set(qn(f'w:{k}'), v)
        borders.append(edge)
    tbl_pr.append(borders)
    for index, row in enumerate(t.rows):
        trpr = row._tr.get_or_add_trPr()
        trpr.append(OxmlElement('w:cantSplit'))
        if index == 0:
            trpr.append(OxmlElement('w:tblHeader'))
        for col, cell in enumerate(row.cells):
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            pr = cell._tc.get_or_add_tcPr()
            margins = OxmlElement('w:tcMar')
            for side in ('top', 'left', 'bottom', 'right'):
                el = OxmlElement(f'w:{side}')
                el.set(qn('w:w'), '90')
                el.set(qn('w:type'), 'dxa')
                margins.append(el)
            pr.append(margins)
            if index == 0:
                shading = OxmlElement('w:shd')
                shading.set(qn('w:fill'), 'E8EDF2')
                pr.append(shading)
            for p in cell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col in numeric else WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.line_spacing = 1.06
                if index == 0:
                    p.paragraph_format.keep_with_next = True
                for r in p.runs:
                    r.font.name = 'Arial'
                    r.font.size = Pt(size)
                    r.font.bold = index == 0
                    r.font.color.rgb = RGBColor(0, 0, 0)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return t


def picture(doc, path, width, caption, alt):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    shape = p.add_run().add_picture(str(path), width=Inches(width))
    shape._inline.docPr.set('descr', alt)
    c = doc.add_paragraph(caption, 'Caption')
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return shape


def mr(text):
    r = OxmlElement('m:r')
    t = OxmlElement('m:t')
    t.text = text
    r.append(t)
    return r


def script(base, sub=None, sup=None):
    tag = 'sSubSup' if sub is not None and sup is not None else 'sSub' if sub is not None else 'sSup'
    n = OxmlElement('m:' + tag)
    e = OxmlElement('m:e')
    for item in base if isinstance(base, list) else [mr(base)]: e.append(item)
    n.append(e)
    if sub is not None:
        el = OxmlElement('m:sub')
        for item in sub if isinstance(sub, list) else [mr(sub)]: el.append(item)
        n.append(el)
    if sup is not None:
        el = OxmlElement('m:sup')
        for item in sup if isinstance(sup, list) else [mr(sup)]: el.append(item)
        n.append(el)
    return n


def radical(items):
    node = OxmlElement('m:rad')
    pr = OxmlElement('m:radPr')
    hide = OxmlElement('m:degHide'); hide.set(qn('m:val'), '1'); pr.append(hide)
    node.append(pr)
    node.append(OxmlElement('m:deg'))
    e = OxmlElement('m:e')
    for item in items: e.append(item)
    node.append(e)
    return node


def frac(top, bottom):
    n = OxmlElement('m:f')
    for name, items in [('num', top), ('den', bottom)]:
        el = OxmlElement('m:' + name)
        for item in items: el.append(item)
        n.append(el)
    return n


def summation(lower, upper, items):
    n = OxmlElement('m:nary')
    pr = OxmlElement('m:naryPr')
    ch = OxmlElement('m:chr'); ch.set(qn('m:val'), '∑'); pr.append(ch)
    loc = OxmlElement('m:limLoc'); loc.set(qn('m:val'), 'subSup'); pr.append(loc)
    if upper == '':
        hide = OxmlElement('m:supHide'); hide.set(qn('m:val'), '1'); pr.append(hide)
    n.append(pr)
    for name, text in [('sub', lower), ('sup', upper)]:
        el = OxmlElement('m:' + name)
        for item in text if isinstance(text, list) else [mr(text)]: el.append(item)
        n.append(el)
    e = OxmlElement('m:e')
    for item in items: e.append(item)
    n.append(e)
    return n


def equation(doc, items):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(5)
    p.paragraph_format.space_after = Pt(8)
    math = OxmlElement('m:oMath')
    for item in items: math.append(item)
    p._p.append(math)
    return p


def link(doc, label, url):
    p = doc.add_paragraph()
    rel = p.part.relate_to(url, RT.HYPERLINK, is_external=True)
    h = OxmlElement('w:hyperlink'); h.set(qn('r:id'), rel)
    r = OxmlElement('w:r'); pr = OxmlElement('w:rPr')
    co = OxmlElement('w:color'); co.set(qn('w:val'), '215A86'); pr.append(co); r.append(pr)
    tx = OxmlElement('w:t'); tx.text = label; r.append(tx); h.append(r); p._p.append(h)


def build_main():
    d = Document(); setup(d)
    d.core_properties.title = 'Algorytm mrówkowy dla problemu komiwojażera'
    d.add_paragraph('Algorytm mrówkowy dla problemu komiwojażera', 'Title')
    d.add_paragraph('Dokumentacja projektu i wyników eksperymentów', 'Subtitle')
    para(d, f'Stan aplikacji {DATE}', size=9.5)
    d.add_paragraph('1 Cel i zakres projektu', 'Heading 1')
    para(d, 'Celem projektu jest zbudowanie interaktywnego laboratorium, które pozwala zrozumieć algorytm mrówkowy, obserwować jego decyzje i sprawdzić jakość znajdowanych tras. Problemem badawczym jest wyznaczenie krótkiego zamkniętego objazdu wszystkich punktów na planszy, czyli rozwiązanie problemu komiwojażera.')
    para(d, 'Projekt powstał na przedmiot Algorytmy inteligentne inspirowane naturą. Głównym rozwiązaniem jest ACO w wariancie Ant System ze strategią elitarną. Aplikacja łączy obliczenia, animację, śledzenie pojedynczej mrówki, porównanie metod i eksport wyników.')
    h2(d, 'Pytania badawcze')
    bullets(d, ['Jak odległość i feromon wpływają na wybór następnego punktu?',
                'Jak zmienia się najlepsza znaleziona długość w kolejnych iteracjach?',
                'Jak ACO wypada na tej samej mapie względem najbliższego sąsiada i 2-opt?',
                'Jak szybko kolonia znajduje dopuszczalną trasę po zamknięciu jednego połączenia?'])
    h2(d, 'Co otrzymuje użytkownik')
    para(d, 'Wejściem są współrzędne mrowiska i punktów pożywienia, zbiór blokad oraz parametry kolonii. Wynikiem są znalezione trasy, ich długości, czasy obliczeń i zapis przebiegu eksperymentu. Interfejs pokazuje także prawdopodobieństwa rzeczywistych wyborów mrówki oraz pozwala zatrzymywać i wykonywać jej ruchy krokowo.')
    h2(d, 'Główny wniosek')
    para(d, 'ACO potrafi stopniowo poprawiać trasę i reagować na zmianę dostępnych połączeń. Jakość wyniku zależy od mapy, parametrów i losowania. Zapisane przykłady pokazują zarówno osiągnięcie optimum na małej mapie, jak i potrzebę dalszego ulepszania pierwszego obejścia po blokadzie. Aplikacja służy do badania tych zależności; nie gwarantuje optimum dla dowolnej instancji.')

    page(d, '2 Model problemu komiwojażera')
    para(d, 'Plansza opisuje symetryczny problem komiwojażera z odległościami euklidesowymi. Punkt 0 jest mrowiskiem, pozostałe punkty reprezentują pożywienie. Przy n punktach pożywienia łączna liczba wierzchołków wynosi N = n + 1.')
    h2(d, 'Odległość i funkcja celu')
    equation(d, [script('d', 'ij'), mr(' = '), radical([
        script([mr('('), script('x', 'i'), mr(' − '), script('x', 'j'), mr(')')], sup='2'),
        mr(' + '), script([mr('('), script('y', 'i'), mr(' − '), script('y', 'j'), mr(')')], sup='2')])])
    equation(d, [mr('L(π) = '), summation('r = 0', 'N − 1', [script('d', [script('π', 'r'), mr(' '), script('π', 'r+1')])]),
                 mr(' ,    '), script('π', 'N'), mr(' = '), script('π', '0'), mr(' = 0')])
    para(d, 'Trasa π ustala kolejność odwiedzania punktów. Minimalizujemy sumę długości kolejnych odcinków. Objazd domykamy powrotem do mrowiska po ostatnim punkcie pożywienia; odległość powrotu również wchodzi do oceny.')
    bullets(d, ['Start i koniec znajdują się w mrowisku.', 'Każdy punkt pożywienia jest odwiedzony dokładnie raz.', 'Zablokowanego odcinka nie wolno przejść w żadnym kierunku.', 'Mniejsza długość oznacza lepszy wynik w obrębie tej samej mapy i tych samych blokad.'])
    h2(d, 'Reprezentacja w programie')
    para(d, 'Macierz odległości ma wymiar N × N. Trasa jest listą indeksów rozpoczynającą się od 0. Powrót do mrowiska jest domyślny, dlatego na końcu listy nie trzeba dopisywać drugiego zera. Zbiór blokad przechowuje pary uporządkowane jako mniejszy indeks i większy indeks.')
    code(d, 'Przykład trasy: [0, 2, 1, 3]\nInterpretacja: 0 → 2 → 1 → 3 → 0')
    para(d, 'W kodzie blokada ma znacznik kosztu 1 000 000. Kolonia jawnie wyklucza takie krawędzie z losowania, także przy β = 0. Ocena zamkniętej trasy z blokadą daje wynik niedopuszczalny. Algorytmy porównawcze nie zgłaszają takiej trasy jako rozwiązania.')
    h2(d, 'Przykład kontrolny i granice modelu')
    para(d, 'Dla czterech narożników kwadratu o boku 100 jednostek najkrótszy objazd ma długość 400. Ten przypadek stanowi prosty punkt odniesienia w testach. Jednostki są jednostkami planszy, a nie kilometrami. Odcinki są połączeniami grafu; ich przecięcie na rysunku nie tworzy nowego skrzyżowania.')
    para(d, 'Zamknięcie wielu połączeń może uniemożliwić pełny objazd. Brak wyniku heurystyki oznacza, że nie znalazła trasy, a nie że udowodniła jej nieistnienie. Dokładne rozstrzygnięcie daje tu przegląd zupełny dla małych map.')

    page(d, '3 Jak mrówka wybiera kolejny punkt')
    para(d, 'ACO należy do metod inteligencji roju. W projekcie każda wirtualna mrówka konstruuje własną trasę. Jej decyzja jest losowa, ale szanse zależą od stanu połączeń. Klasyczną podstawę tej rodziny metod opisali Dorigo, Maniezzo i Colorni [1]. Reguły przedstawione niżej odpowiadają implementacji w algorytmy.py.')
    h2(d, 'Reguła wyboru')
    numerator = [script('τ', 'ij', 'α'), mr(' '), script('η', 'ij', 'β')]
    denominator = [summation([mr('ℓ ∈ '), script('A', 'k'), mr('(i)')], '',
                            [script('τ', 'iℓ', 'α'), mr(' '), script('η', 'iℓ', 'β')])]
    equation(d, [script('p', 'ij', '(k)'), mr(' = '), frac(numerator, denominator)])
    para(d, 'τ oznacza feromon, η = 1/d jest widocznością, α określa znaczenie feromonu, a β wpływ odległości. Aₖ(i) obejmuje jeszcze nieodwiedzone punkty dostępne z miejsca i dla mrówki k. Punkty odwiedzone i zamknięte odcinki mają prawdopodobieństwo 0.')
    para(d, 'Program losuje ruch zgodnie z otrzymanym rozkładem. Punkt z najwyższą szansą nie jest wybierany zawsze. Ta możliwość próbowania różnych tras pozwala badać rozwiązania poza jedną zachłanną kolejnością. Jeżeli wszystkie wagi dostępnych ruchów zanikną numerycznie, wybór jest równomierny wśród legalnych możliwości.')
    h2(d, 'Przykład liczbowy')
    para(d, 'Załóżmy dwa dostępne punkty, równy feromon oraz β = 3. Odległości wynoszą 100 i 200. Wagi są proporcjonalne do 1/100³ i 1/200³, czyli pozostają w stosunku 8 do 1.')
    table(d, ['Punkt', 'Odległość', 'Szansa wyboru'], [('A', '100', '88,9%'), ('B', '200', '11,1%')], [3, 5.5, 8.3], numeric=(1, 2))
    para(d, 'Przy β = 0 i nadal równym feromonie oba dostępne punkty miałyby po 50%. Z kolei α = 0 usuwa wpływ feromonu, zachowując wpływ odległości i blokad.')
    picture(d, ASSETS / 'sledzona_mrowka.png', 4.25,
            'Panel rzeczywistej decyzji na mapie aplikacji. Dane panelu dotyczą innego układu niż przykład A i B.',
            'Panel śledzonej mrówki z szansami kilku kolejnych punktów i zaznaczonym wylosowanym ruchem')

    page(d, '4 Pamięć kolonii i parowanie feromonu')
    para(d, 'Po ukończeniu rundy program ocenia dopuszczalne trasy. Mrówki z krótszymi trasami odkładają większą ilość feromonu. Dodatkowe wzmocnienie otrzymuje najlepsza znaleziona dotąd trasa. Jest to zastosowana w projekcie strategia elitarna.')
    equation(d, [script('τ', 'ij'), mr(' ← (1 − ρ)'), script('τ', 'ij'), mr(' + '),
                 summation('k = 1', 'm', [script('Δτ', 'ij', '(k)')]), mr(' + e '), script('Δτ', 'ij', 'best')])
    equation(d, [script('Δτ', 'ij', '(k)'), mr(' = '), frac([mr('Q')], [script('L', 'k')])])
    para(d, 'Przyrost Q/Lₖ dotyczy krawędzi wykorzystanych przez daną mrówkę. Dla pozostałych wynosi 0. Analogiczny przyrost na najlepszej trasie jest mnożony przez e. Mrówki, które utknęły lub nie ukończyły dopuszczalnego objazdu, nie odkładają feromonu.')
    table(d, ['Parametr', 'Wartość domyślna', 'Znaczenie w tym projekcie'], [
        ('m', '20 mrówek', 'Liczba prób budowy trasy w jednej rundzie; suwak 5–100.'),
        ('α', '1,0', 'Wpływ feromonu; suwak 0–5. Wartość 0 wyłącza ten wpływ.'),
        ('β', '3,0', 'Wpływ odwrotności odległości; suwak 0–10.'),
        ('ρ', '0,3', 'Część odparowującego feromonu; suwak 0,01–0,9.'),
        ('Q', '1,0', 'Skala przyrostu feromonu, ustalana w kodzie.'),
        ('e', '1,0', 'Waga dodatkowego wzmocnienia najlepszej trasy, ustalana w kodzie.')], [1.8, 3.7, 11.3], numeric=(0, 1))
    h2(d, 'Dlaczego feromon paruje')
    para(d, 'Mnożenie przez 1 − ρ stopniowo osłabia stare ślady. Bez osłabiania dawne wybory mogłyby zdominować poszukiwanie. Zbyt duże znaczenie feromonu może jednak skupić kolonię na wcześnie znalezionej trasie; małe parowanie również może utrwalać wcześniejsze preferencje. Zależności te można sprawdzać zmianą parametrów i wykresem zbieżności.')
    h2(d, 'Stabilność obliczeń i chwila aktualizacji')
    para(d, 'Początkowy poziom feromonu wynika z długości trasy zachłannej. Program utrzymuje dolną granicę 10⁻³ τ₀ i zabezpiecza dzielenie przez zerową długość. Podczas animowanej rundy trasy i ich decyzje są już ustalone, a feromon aktualizuje się dopiero po zakończeniu wszystkich podróży.')
    para(d, 'Zmiana α, β i liczby mrówek dotyczy kolejnej budowy tras. Współczynnik ρ jest stosowany przy aktualizacji na końcu rundy. Prędkość odtwarzania wpływa na animację, a nie na regułę losowania.')

    page(d, '5 Metody porównawcze i koszt obliczeń')
    para(d, 'Na tej samej macierzy odległości uruchamiane są trzy heurystyki i, dla małych przypadków, metoda dokładna. W projekcie 2-opt rozpoczyna od wyniku zachłannego najbliższego sąsiada. Jego klasycznym punktem odniesienia jest praca Croesa [2].')
    table(d, ['Metoda', 'Zasada', 'Gwarancja'], [
        ('ACO', 'Wiele losowych tras, pamięć feromonowa, parowanie i wzmocnienie elitarne.', 'Najlepszy znaleziony wynik; brak ogólnej gwarancji optimum.'),
        ('Najbliższy sąsiad', 'Zawsze następny najbliższy nieodwiedzony punkt.', 'Szybka trasa zachłanna; może być daleka od optimum.'),
        ('2-opt', 'Zamiana dwóch połączeń i odwrócenie fragmentu, jeśli skraca to trasę.', 'Optimum lokalne względem sprawdzanych zamian.'),
        ('Przegląd zupełny', 'Ocena wszystkich kolejności z pominięciem odbicia tej samej trasy.', 'Optimum lub stwierdzenie braku cyklu w badanej instancji.')], [3.2, 7.4, 6.2])
    h2(d, 'Jak działa zamiana w 2 opt')
    para(d, 'Dla odcinków a–b i c–d rozważamy połączenia a–c i b–d. Jeżeli nowa suma długości jest mniejsza, odwracamy fragment pomiędzy b i c. Powtarzamy przeglądy, dopóki znajdujemy poprawę. Zakończenie takiego procesu nie dowodzi, że nie istnieje lepsza trasa wymagająca innych zmian.')
    equation(d, [mr('Δ = d(a,c) + d(b,d) − d(a,b) − d(c,d)')])
    h2(d, 'Skalowanie zastosowanych implementacji')
    table(d, ['Metoda', 'Koszt i ograniczenia'], [
        ('Najbliższy sąsiad', 'O(N²): w każdym kroku przegląd pozostałych punktów.'),
        ('ACO', 'W przybliżeniu O(T m N²) dla T iteracji. Macierze odległości i feromonu wymagają O(N²) pamięci.'),
        ('2-opt', 'Przegląd par wymaga O(N²) porównań. Odwracanie zaakceptowanego fragmentu dodatkowo kosztuje O(N); liczba przejść zależy od danych.'),
        ('Przegląd zupełny', 'n! kolejności; ocena jednej trasy do O(N). Odcięcia skracają część obliczeń, lecz nie usuwają silniowego wzrostu.')], [4.3, 12.5])
    para(d, 'N oznacza liczbę wszystkich punktów z mrowiskiem, a n liczbę punktów pożywienia. Interfejs ogranicza przegląd zupełny do n ≤ 10. Zapis pełnych prawdopodobieństw każdej decyzji na potrzeby śledzenia dodaje koszt pamięci rzędu O(m N²); szybkie eksperymenty pomijają ten zapis.')
    para(d, 'Przy blokadach trasa zachłanna lub lokalne ulepszanie mogą nie znaleźć rozwiązania, mimo że inna kolejność byłaby dopuszczalna. Interfejs wyświetla wtedy brak znalezionej trasy, zamiast traktować odcinek zamknięty jak zwykły objazd z dużym kosztem.')

    page(d, '6 Architektura i odpowiedzialność modułów')
    para(d, 'Logika eksperymentu jest oddzielona od Pygame. Dzięki temu stan kolonii, pauzę, pojedynczy ruch, blokady i wyścig można sprawdzić bez otwierania okna. Rysowanie nie decyduje o wyniku algorytmu.')
    code(d, 'Zdarzenia użytkownika → App → SimulationSession → algorytmy\nStan sesji → widoki Pygame\nMigawka wyników → raporty PNG CSV JSON')
    table(d, ['Plik lub grupa', 'Odpowiedzialność'], [
        ('aplikacja.py', 'Punkt uruchomienia, tryb okna i konfiguracja wyświetlania.'),
        ('algorytmy.py', 'Macierz odległości, metody TSP oraz niezmienny zapis decyzji i podróży.'),
        ('mrowisko/symulacja.py', 'Właściciel stanu planszy, kolonii, podróży, czasu odtwarzania, blokady i bieżącego wyścigu.'),
        ('mrowisko/wyscig.py', 'Niezależne obliczenia trzech metod na tej samej niezmiennej kopii problemu.'),
        ('mrowisko/interfejs.py', 'Przekładanie klawiatury i myszy na polecenia; przełączanie widoków i podsumowań.'),
        ('plansza.py i widok_wyscigu.py', 'Rysowanie kolonii, feromonu, śledzenia, banerów oraz trzech plansz wyścigu.'),
        ('eksperyment.py i raporty.py', 'Zapis obserwacji, migawka danych i tworzenie plików wynikowych.'),
        ('panel.py kontrolki.py objasnienia.py motyw.py', 'Przyciski, suwaki, historia, wzory, podglądy i wspólna geometria interfejsu.'),
        ('scenariusze.py i porownanie.py', 'Gotowe mapy prezentacji oraz niezależny zestaw badań porównawczych.')], [6.1, 10.7])
    h2(d, 'Dane które warto rozróżniać')
    para(d, 'Decision utrwala wybrany ruch i prawdopodobieństwa w chwili losowania. Journey opisuje całą podróż jednej mrówki i informuje, czy udało się ją dokończyć. AntState przekazuje pozycję i stan odtwarzania do widoku. RoadClosure przechowuje chwilę blokady, starą trasę i pierwszy wynik po zmianie problemu.')
    h2(d, 'Dlaczego wyścig ma własną kolonię')
    para(d, 'Wyścig wykonuje eksperyment na kopii mapy, blokad, ziarna i parametrów. Nie przejmuje feromonu z otwartej animacji. Dzięki temu metody dostają ten sam problem, a zmiana suwaków nie zmienia w trakcie rozpoczętego porównania jego warunków. Decyzje architektoniczne zapisano w docs/adr/.')

    page(d, '7 Uruchomienie i obsługa aplikacji')
    para(d, 'Wymagany jest Python 3.10 lub nowszy oraz biblioteki Pygame, NumPy i Matplotlib z requirements.txt. Pygame obsługuje okno i zdarzenia, NumPy macierze i losowanie, a Matplotlib wykresy. Zalecane jest osobne środowisko wirtualne.')
    code(d, 'python3 -m venv .venv\n.venv/bin/python -m pip install -r requirements.txt\n.venv/bin/python aplikacja.py --okno')
    para(d, 'Na Windows można użyć uruchom.bat albo odpowiednika .venv\\Scripts\\python.exe. Bez parametru --okno program uruchamia pełny ekran. Do działania kolonii potrzeba mrowiska i co najmniej dwóch punktów pożywienia.')
    table(d, ['Sterowanie', 'Efekt'], [
        ('LPM na pustej planszy', 'Dodanie punktu pożywienia i reset kolonii.'),
        ('Przeciągnięcie punktu', 'Zmiana położenia punktu lub mrowiska i reset eksperymentu.'),
        ('PPM na pożywieniu', 'Usunięcie punktu; mrowiska nie można usunąć.'),
        ('Spacja', 'Start lub pauza całej kolonii albo wyścigu.'),
        ('F', 'Wybór śledzonej mrówki; w wyścigu przycisk służy do nowego wyścigu, a skrót wywołuje tę samą akcję.'),
        ('N', 'Następny punkt śledzonej mrówki; w wyścigu jeden wspólny krok.'),
        ('S', 'Dokończenie jednej rundy kolonii lub jeden krok wyścigu.'),
        ('R i C', 'Losowanie punktów lub wyczyszczenie planszy.'),
        ('B', 'Edycja blokad przez kliknięcie odcinka.'),
        ('I', 'Panel wzorów i klasyfikacji algorytmu.'),
        ('W i K', 'Szanse dla wskazanego punktu oraz osobny podgląd zachłanny.'),
        ('A', 'Animacja mrówek lub szybkie obliczenia; bieżąca niezatwierdzona podróż jest porzucana.'),
        ('P', 'Tabela porównania metod. Kliknięcie wiersza pokazuje daną trasę.'),
        ('V i G', 'Wyścig lub powrót do kolonii; wykresy lub powrót z podsumowania.'),
        ('F11 i Esc', 'Przełączenie okna i pełnego ekranu; zamknięcie programu.')], [4, 12.8], size=9.3)
    para(d, 'W śledzeniu pauza zatrzymuje wszystkie mrówki. Następny ruch przesuwa całą kolonię o odległość potrzebną wybranej mrówce do dotarcia do kolejnego punktu. Pozostałe mogą w tym czasie przejść przez inną liczbę punktów. Aktualizacja feromonu czeka na ostatnią podróż.')

    page(d, '8 Scenariusze prezentacji i wyścig metod')
    table(d, ['Scenariusz', 'Cel pokazu'], [
        ('Pierwsza kolonia', 'Poznanie feromonu, ruchu i rzeczywistych wyborów mrówki.'),
        ('Pułapka najbliższego sąsiada', 'Przykład, na którym zachłanny wybór tworzy trasę o ponad 25% dłuższą od optimum.'),
        ('Bez feromonu', 'α = 0: ślady powstają, ale nie uczestniczą w regule wyboru.'),
        ('Zablokowana droga', 'Zmiana dostępnych połączeń i pomiar pierwszego dopuszczalnego obejścia.')], [5.5, 11.3])
    para(d, 'Każdy scenariusz ma przygotowaną mapę, parametry i ziarno losowania. Jego ponowne wybranie rozpoczyna pokaz od nowa. Proporcje mapy są zachowane przy skalowaniu; powtarzalność przykładu należy odnosić do tych samych współrzędnych i ustawień.')
    picture(d, ROOT / 'wyniki/podglad/wyscig.png', 6.3,
            'Trzy plansze wyścigu na tej samej mapie. Poniżej tras widoczne są długości i czasy obliczeń.',
            'Widok wyścigu ACO najbliższego sąsiada i 2-opt z identyczną geometrią punktów')
    h2(d, 'Co oznacza synchronizacja')
    para(d, 'Wspólny krok przesuwa każdą niezakończoną metodę do kolejnego widocznego wyniku. Dla ACO jest to iteracja, dla najbliższego sąsiada kolejny etap budowy trasy, a dla 2-opt budowa startowej trasy lub poprawa połączeń. Zakończona metoda pozostaje na ekranie, gdy inne jeszcze pracują.')
    para(d, 'Kroki nie oznaczają równego nakładu pracy ani równoległego wykonania na trzech procesorach. Czas każdej metody jest sumowany osobno wokół jej obliczeń. Podawane odchylenie od optimum dotyczy tylko przypadku, w którym wyznaczono dokładny wynik odniesienia.')

    page(d, '9 Zamknięcie drogi i pomiar obejścia')
    para(d, 'Najpierw uruchamiamy kolonię na scenariuszu Zablokowana droga. Po uzyskaniu trasy wybieramy Zablokuj drogę i klikamy wybrany odcinek złotej trasy. Program wznawia szukanie, oznacza zamknięcie na czerwono i pokazuje licznik zakończonych iteracji od zmiany problemu.')
    h2(d, 'Zmiana stanu eksperymentu')
    bullets(d, ['Zapisujemy numer iteracji, starą trasę, jej długość i historię sprzed blokady.',
                'Unieważniamy trasę korzystającą z zamkniętego odcinka.',
                'Odrzucamy niezatwierdzone podróże i śledzenie, zachowując dotychczasowy feromon.',
                'Budujemy następne podróże już z bezwzględnym zakazem wybranej krawędzi.',
                'Przy pierwszej dopuszczalnej trasie utrwalamy liczbę iteracji i czas obliczeń do obejścia.'])
    picture(d, ASSETS / 'baner_blokady.png', 6.2,
            'Baner podczas poszukiwania. Wartość 0 oznacza, że pierwsza nowa runda jeszcze się nie zakończyła.',
            'Czerwony baner informujący o zamknięciu drogi i liczbie iteracji od blokady')
    h2(d, 'Pierwsze obejście i dalsze ulepszanie')
    para(d, 'Pierwsze obejście jest pełnym dopuszczalnym objazdem omijającym blokady. Nie stawiamy tu warunku osiągnięcia optimum ani określonej jakości. Licznik w modelu aktualizuje się po każdej iteracji, dlatego szybkie wykonanie kilku iteracji naraz nie zmienia momentu pierwszego sukcesu.')
    para(d, 'Po odzyskaniu trasy aplikacja zatrzymuje się na wynik i pokazuje podsumowanie. Można wrócić klawiszem G i wznowić obliczenia, aby sprawdzić dalszą poprawę. Kolejne podsumowanie zapisuje aktualny przebieg. Otworzenie drogi usuwa bieżący zapis tego zdarzenia z sesji; wcześniej wyeksportowane pliki pozostają.')
    h2(d, 'Sytuacje graniczne')
    para(d, 'Jeżeli zamknięty odcinek nie należał do aktualnej najlepszej trasy, może ona pozostać dopuszczalna od razu; wtedy liczba nowych iteracji wynosi 0. Przy braku rozwiązania lub nieudanych próbach licznik rośnie, a program nie zgłasza fikcyjnego obejścia. Brak wyniku ACO nie jest dowodem braku cyklu w grafie.')

    page(d, '10 Metodyka badań i zapis wyników')
    para(d, 'Projekt udostępnia pojedynczy wyścig prezentacyjny oraz osobny skrypt porownanie.py do serii badań. Nie należy utożsamiać pojedynczego udanego pokazu z wnioskiem statystycznym o przewadze jednej metody.')
    table(d, ['Badanie w porownanie.py', 'Warunki'], [
        ('Małe mapy', '3–10 punktów pożywienia, porównanie z optimum. Standardowo 5 powtórzeń, w trybie szybkim 2.'),
        ('Większe mapy', '10, 20, 30, 50, 75 i 100 punktów. Standardowo 3 powtórzenia, szybko 2. Odniesieniem jest najlepszy wynik badanych metod, nie udowodnione optimum.'),
        ('Zbieżność', '30 punktów i 150 iteracji, po 3 ziarna losowania dla pięciu wariantów α β ρ.'),
        ('Blokada', '20 punktów, 100 iteracji rozgrzewki, maksymalnie 300 dalszych iteracji; 10 powtórzeń lub 3 w trybie szybkim.')], [5, 11.8])
    para(d, 'Standardowe ACO w porównaniu rozmiarów wykonuje 100 iteracji, używa 20 mrówek oraz α = 1, β = 3 i ρ = 0,3. Dla optimum L* nadwyżka wynosi 100 · (L/L* − 1)%. Dla większych map analogiczny procent wobec najlepszego znalezionego wyniku nie jest miarą błędu względem optimum.')
    h2(d, 'Dwa różne kryteria po blokadzie')
    para(d, 'Interfejs mierzy pierwsze dopuszczalne obejście. Skrypt badawczy mierzy dodatkowo dojście do trasy co najwyżej o 3% dłuższej od wyniku 2-opt na zmienionej mapie. Wynik 2-opt jest punktem odniesienia, a nie gwarantowanym optimum. Wartość 300 w przypadku braku osiągnięcia progu jest limitem obserwacji, więc nie wolno interpretować jej jako dokładnego czasu sukcesu.')
    h2(d, 'Zapisane przykłady opisane w dokumentacji')
    table(d, ['Przypadek', 'Warunki i dane'], [
        ('Wyścig', 'Mapa Pułapka najbliższego sąsiada, 6 punktów pożywienia, ziarno 12, 20 mrówek, 100 iteracji, standardowe α β ρ.'),
        ('Blokada', 'Mapa Zablokowana droga, 7 punktów pożywienia, ziarno 11, 50 iteracji przed i 50 po zamknięciu odcinka 3–4.')], [4, 12.8])
    para(d, 'Wykresy na kolejnych stronach pochodzą z raportów zapisanych 15 listopada 2026. Długości są w jednostkach planszy. Czasy odnoszą się do jednego uruchomienia na użytym komputerze; drobne wartości mikrosekundowe są szczególnie wrażliwe na narzut i obciążenie systemu.')
    para(d, 'Podsumowanie zapisuje podsumowanie.png, wyniki.csv i dane.json, a wyścig także postep_aco.csv. JSON zawiera mapę, blokady, parametry, ziarno i przebieg. Brak wartości jest zapisywany jako null zamiast błędnej liczby 0. Każdy eksport ma osobny katalog w wyniki/eksperymenty/.')

    page(d, '11 Wyniki przykładowego wyścigu', wide=True)
    picture(d, RACE_DIR / 'podsumowanie.png', 9.7,
            'Zapisany wyścig na mapie Pułapka najbliższego sąsiada. Czas wyznaczenia optimum jest mierzony osobno.',
            'Trzy wykresy długości tras czasu obliczeń i postępu ACO z dokładnym optimum jako odniesieniem')

    page(d, '12 Wyniki przykładowej blokady', wide=True)
    picture(d, CLOSURE_DIR / 'podsumowanie.png', 9.7,
            'Zamknięcie po iteracji 50. Pierwsze obejście powstało w iteracji 51; późniejsze obliczenia dalej skracały trasę.',
            'Przebieg długości trasy przed i po zamknięciu drogi tabela wyników oraz stara i nowa trasa na mapie')

    page(d, '13 Interpretacja wyników i weryfikacja')
    results = RACE['results']
    table(d, ['Metoda', 'Długość', 'Nadwyżka', 'Czas obliczeń'],
          [(r['name'], num(r['length']), num(r['gap'], 2) + '%', num(r['seconds'] * 1000, 3) + ' ms') for r in results],
          [5.5, 3.5, 3.5, 4.3], numeric=(1, 2, 3))
    para(d, f"Dokładne optimum ma długość {num(RACE['optimum'])}. ACO osiągnął je w zapisanej próbie; najbliższy sąsiad uzyskał trasę o {num(results[1]['gap'], 2)}% dłuższą, a 2-opt o {num(results[2]['gap'], 2)}% dłuższą. Najbliższy sąsiad i 2-opt potrzebowały znacznie mniej czasu. Pokaz ilustruje kompromis pomiędzy jakością a kosztem obliczeń, zależny od konkretnej instancji.")
    first = next(s for s in CLOSURE['after'] if s[1] is not None)
    table(d, ['Etap blokady', 'Iteracja', 'Długość'], [
        ('Ostatni wynik przed zamknięciem', CLOSURE['iteration_closed'], num(CLOSURE['old_length'])),
        ('Pierwsze dopuszczalne obejście', first[0], num(first[1])),
        ('Najlepszy wynik na końcu próby', CLOSURE['current_iteration'], num(CLOSURE['length']))], [9, 3, 4.8], numeric=(1, 2))
    para(d, f"Pierwsze obejście znaleziono po {CLOSURE['found_after']} nowej iteracji, w czasie obliczeń {num(CLOSURE['recovery_seconds'] * 1000, 3)} ms. Jego długość {num(first[1])} była większa od późniejszego wyniku {num(CLOSURE['length'])}. Szybka adaptacja nie oznacza natychmiastowego odzyskania najlepszej jakości. Stara trasa po zamknięciu odcinka nie jest już dopuszczalnym konkurentem.")
    h2(d, 'Sprawdzenie zachowania programu')
    para(d, 'Aktualny zestaw obejmuje 18 testów. Sprawdzają one zakaz przejścia przez blokadę przy β = 0, zapis rzeczywistych szans, pauzę i krok, aktualizację feromonu po wszystkich podróżach, zmianę liczby mrówek, reset scenariuszy, pierwszy moment obejścia oraz wyścig na mapie o znanym optimum i mapie bez cyklu.')
    para(d, 'Osobny skrypt narzedzia/sprawdz_interfejs.py uruchamia Pygame bez okna, wysyła zdarzenia kliknięć i klawiatury oraz zapisuje zrzuty. Sprawdza wybór mrówki, scenariusze, kliknięcie blokady, wyścig i eksport. Testy stanu nie zastępują wizualnej kontroli płynności na docelowym komputerze.')
    h2(d, 'Ograniczenia wyników')
    bullets(d, ['ACO jest losowy, a 2-opt kończy w optimum lokalnym. Wynik jednej mapy nie opisuje wszystkich problemów TSP.',
                'Dłuższy budżet ACO i inne parametry mogą zmienić porównanie. Animacyjny krok nie wyrównuje nakładu pracy metod.',
                'Stary feromon może ułatwić lub utrudnić adaptację. Samo jego zachowanie nie gwarantuje szybszej trasy dobrej jakości.'])

    page(d, '14 Wnioski odtworzenie i źródła')
    h2(d, 'Co projekt pokazuje')
    para(d, 'Najważniejszym wynikiem projektu jest możliwość połączenia reguł matematycznych z obserwowalnym zachowaniem kolonii. Użytkownik może prześledzić rzeczywisty losowy wybór, zobaczyć narastanie preferencji tras, porównać metody na jednej mapie i zmierzyć reakcję na zmianę problemu. Taka forma pozwala wyjaśnić zarówno zalety poszukiwania opartego na feromonie, jak i jego ograniczenia.')
    h2(d, 'Jak odtworzyć sprawdzenie')
    code(d, 'python3 -m unittest discover -s tests -v\npython3 narzedzia/sprawdz_interfejs.py\npython3 narzedzia/demo_eksperymenty.py\npython3 porownanie.py --szybko')
    para(d, 'Pierwsze polecenie sprawdza zachowanie modelu, drugie przepływy interfejsu, trzecie tworzy dwa kompletne przykłady raportów, a czwarte uruchamia skróconą serię badań. Czasy przy ponownym wykonaniu będą inne; porównywanie długości wymaga tych samych współrzędnych, parametrów, ziarna i budżetu.')
    h2(d, 'Kierunki dalszych prac')
    para(d, 'Kolejne rozszerzenia można oceniać przez większe zbiory map, więcej niezależnych uruchomień i rozrzut wyników zamiast samych średnich. W badaniu blokad warto osobno zapisywać nieosiągnięcie progu w limicie. Rozszerzeniem algorytmicznym mogłoby być połączenie ACO z lokalnym 2-opt; wymagałoby to osobnego wariantu porównania i ponownego pomiaru kosztu.')
    h2(d, 'Literatura')
    para(d, '[1] M. Dorigo, V. Maniezzo, A. Colorni. Ant System: Optimization by a Colony of Cooperating Agents. IEEE Transactions on Systems, Man, and Cybernetics Part B, 26(1), 29–41, 1996.')
    link(d, 'DOI 10.1109/3477.484436', 'https://doi.org/10.1109/3477.484436')
    para(d, '[2] G. A. Croes. A Method for Solving Traveling-Salesman Problems. Operations Research, 6(6), 791–812, 1958.')
    link(d, 'DOI 10.1287/opre.6.6.791', 'https://doi.org/10.1287/opre.6.6.791')
    h2(d, 'Materiały projektu')
    para(d, 'Opis implementacji oparto na algorytmy.py, mrowisko/symulacja.py, wyscig.py, eksperyment.py, interfejs.py i porownanie.py. Warunki użycia zawiera README.md, a decyzje o rozdzieleniu animacji i wyścigu zapisano w docs/adr/.')
    code(d, 'wyniki/eksperymenty/race_20261115_173237_803615/dane.json\nwyniki/eksperymenty/closure_20261115_173238_202521/dane.json')
    para(d, 'Wartości liczbowe i ilustracje na stronach wyników pochodzą z powyższych zapisów. Objaśnienia reguł opisują konkretny wariant projektu, a nie wszystkie odmiany ACO. Stan dokumentacji i wynik weryfikacji: ' + DATE + '.', size=9.5)
    path = OUT / 'Dokumentacja_ACO_TSP_aktualna.docx'
    d.save(path)
    return path


def build_talk():
    d = Document(); setup(d)
    d.core_properties.title = 'Jak przedstawić projekt ACO dla problemu komiwojażera'
    d.add_paragraph('Jak przedstawić projekt ACO dla problemu komiwojażera', 'Title')
    d.add_paragraph('Scenariusz wystąpienia i pokazu na 8 do 10 minut', 'Subtitle')
    d.add_paragraph('Cel i plan wystąpienia', 'Heading 1')
    para(d, 'Cel wystąpienia: wyjaśnić, jaki problem rozwiązujemy, pokazać decyzję jednej mrówki i zachowanie kolonii oraz zinterpretować wyniki porównania i blokady.')
    h2(d, 'Gotowe otwarcie')
    para(d, 'Zbudowaliśmy interaktywne laboratorium algorytmu mrówkowego. Na planszy mamy mrowisko i punkty pożywienia. Szukamy możliwie krótkiej trasy, która odwiedza każdy punkt dokładnie raz i wraca do początku. To problem komiwojażera. Chcemy pokazać, jak wiele prostych losowych decyzji, wspomaganych wspólną pamięcią feromonową, prowadzi do coraz lepszych tras. Następnie sprawdzamy wynik na tle innych metod i obserwujemy reakcję na zamknięcie drogi.')
    h2(d, 'Plan czasu')
    table(d, ['Czas', 'Co wyjaśnić i pokazać'], [
        ('0–1 min', 'Cel projektu i warunki problemu TSP.'),
        ('1–3 min', 'Pierwsza kolonia, feromon, śledzenie mrówki i jeden krok.'),
        ('3–4 min', 'Wzór wyboru oraz znaczenie α β ρ.'),
        ('4–6 min', 'Pułapka najbliższego sąsiada i wyścig trzech metod.'),
        ('6–8 min', 'Zamknięcie odcinka złotej trasy i licznik pierwszego obejścia.'),
        ('8–10 min', 'Wykresy, ograniczenia pomiaru i wniosek końcowy.')], [3.2, 13.6], numeric=(0,))
    h2(d, 'Przygotowanie przed wystąpieniem')
    bullets(d, ['Uruchom python3 aplikacja.py --okno i sprawdź, czy okno oraz tekst są czytelne na projektorze.',
                'Miej przygotowane oba zapisane wykresy z dokumentacji jako wariant awaryjny.',
                'Przećwicz klawisze: Spacja, F, N, I, V i G. Dla pokazu blokady ustaw prędkość odtwarzania około 3.',
                'Na planszy zaznacz, gdzie jest mrowisko, a gdzie punkty pożywienia. Nie zaczynaj od omawiania plików programu.'])
    para(d, 'Główna myśl do zapamiętania: projekt pokazuje związek między regułą wyboru pojedynczej mrówki, pamięcią kolonii i jakością całej trasy. Wyniki liczbowe mają sens dopiero wraz z warunkami eksperymentu.', bold=True)

    page(d, 'Pokaz na żywo od celu do zamknięcia drogi')
    h2(d, 'Etap 1 Pierwsza kolonia')
    para(d, 'Na ekranie wybierz Pierwsza kolonia i uruchom Start. Po chwili zatrzymaj Spacją. Wybierz Śledź mrówkę lub F, a następnie N. Zwróć uwagę na panel prawdopodobieństw i złoty znacznik wybranego ruchu.')
    para(d, 'Powiedz: Każda mrówka układa własny objazd. Przy wyborze następnego punktu bierze pod uwagę odległość i feromon. Wybór pozostaje losowy. Największa szansa oznacza częsty wybór, ale nie pewność. Panel pokazuje szanse zapisane dla tej konkretnej decyzji, więc możemy połączyć obliczenia z ruchem na planszy.')
    h2(d, 'Etap 2 Feromon i parametry')
    para(d, 'Otwórz I i krótko pokaż regułę. Wyjaśnij: α zwiększa znaczenie feromonu, β znaczenie krótszych odległości, a ρ określa parowanie. Krótsza ukończona trasa zostawia więcej feromonu; najlepsza dotąd trasa jest dodatkowo wzmacniana. Aktualizacja następuje po zakończeniu wszystkich podróży. Zamknij I.')
    para(d, 'Przykład do powiedzenia: Jeśli feromon jest równy, a odległości do dwóch punktów wynoszą 100 i 200, przy β = 3 szanse wynoszą około 89% i 11%. Gdy ustawimy α = 0, wyłączamy wpływ feromonu. Odpowiada temu gotowy scenariusz Bez feromonu.')
    h2(d, 'Etap 3 Wyścig metod')
    para(d, 'Wybierz Pułapka najbliższego sąsiada, następnie V i Start. Podczas pracy omów różnice: najbliższy sąsiad wybiera zachłannie, 2-opt ulepsza jego trasę, a ACO wykonuje wiele losowych prób. Dokończ pokaz do automatycznego podsumowania.')
    para(d, 'Powiedz: Metody dostają dokładnie tę samą mapę. Wspólny krok służy prezentacji i nie oznacza tej samej liczby operacji. Porównujemy osobno długość trasy i rzeczywisty czas obliczeń. Dla tej małej mapy znamy optimum, bo sprawdziliśmy wszystkie kolejności. ACO jest tutaj najdokładniejszy, ale metody zachłanne są znacznie szybsze.')
    h2(d, 'Etap 4 Zamknięcie drogi')
    para(d, 'Wybierz Zablokowana droga. Wykonaj kilka rund klawiszem S, aby powstała trasa i feromon. Ustaw prędkość około 3. Kliknij Zablokuj drogę, potem odcinek złotej trasy. Szukanie ruszy automatycznie. Nie naciskaj od razu Start, bo przycisk pełni już funkcję pauzy.')
    para(d, 'Powiedz: Zmieniamy warunki problemu. Zamknięty odcinek jest niedostępny. Unieważniamy podróże rozpoczęte przed zmianą, ale zachowujemy feromon. Licznik mierzy nowe iteracje do pierwszego dopuszczalnego obejścia. Taki objazd może być początkowo długi, a dalsze obliczenia mogą go poprawić.')
    para(d, 'Wartości pokazu na żywo zależą od wybranego odcinka i chwili blokady. Zapisany przykład z dokumentacji ma dokładnie 50 iteracji przed zamknięciem odcinka 3–4 i 50 po nim. Nie utożsamiaj go z dowolnym kliknięciem podczas wystąpienia.', size=9.5)

    page(d, 'Jak opowiedzieć o wynikach eksperymentu')
    h2(d, 'Porównanie na mapie z pułapką')
    table(d, ['Metoda', 'Długość', 'Nadwyżka nad optimum'],
          [(r['name'], num(r['length']), num(r['gap'], 2) + '%') for r in RACE['results']], [6.4, 4.2, 6.2], numeric=(1, 2))
    para(d, 'Powiedz: Optimum tej mapy wynosi 1387,8 jednostki. W zapisanym uruchomieniu ACO osiągnął tę wartość. Trasa najbliższego sąsiada jest o 26,44% dłuższa, a 2-opt zmniejsza tę różnicę do 3,79%. Ta mapa dobrze pokazuje, dlaczego najbliższy punkt nie zawsze prowadzi do najlepszego całego objazdu.')
    para(d, 'W tej próbie 100 iteracji ACO trwało około 90,434 ms. Najbliższy sąsiad potrzebował około 0,010 ms, a 2-opt 0,030 ms. Podaj je jako wyniki konkretnego pomiaru, nie stałe cechy algorytmów. Na własnym komputerze odczytaj wartości z bieżącego podsumowania.')
    h2(d, 'Reakcja na zamknięcie odcinka')
    first = next(s for s in CLOSURE['after'] if s[1] is not None)
    table(d, ['Moment', 'Iteracja', 'Długość'], [
        ('Przed blokadą', '50', num(CLOSURE['old_length'])),
        ('Pierwsze obejście', '51', num(first[1])),
        ('Koniec zapisanej próby', '100', num(CLOSURE['length']))], [8, 3.5, 5.3], numeric=(1, 2))
    para(d, 'Powiedz: Obejście powstało po jednej nowej iteracji, ale miało długość 1914,2. Dalsze obliczenia skróciły wynik do 1705,6. Widać więc różnicę między szybkim odzyskaniem dopuszczalnej trasy a osiągnięciem dobrej jakości. Dawna trasa długości 1675,5 po zamknięciu drogi nie jest już dopuszczalna.')
    h2(d, 'Jak czytać osie i podsumowanie')
    bullets(d, ['Na wykresie ACO oś pozioma oznacza iteracje kolonii, a pionowa najlepszą znalezioną długość.',
                'Wartości pod planszami mierzą obliczenia, nie czas ruchu owadów. Wykres czasu może używać skali logarytmicznej.',
                'Przy blokadzie linia pionowa wskazuje zmianę problemu. Luki oznaczają brak znalezionej dopuszczalnej trasy.',
                'G wraca z podsumowania. Po powrocie można wznowić obliczenia, a kolejne G zapisze aktualny przebieg.'])
    h2(d, 'Gotowe zakończenie')
    para(d, 'Projekt pozwala zobaczyć, jak lokalne losowe wybory i wspólna pamięć prowadzą do poszukiwania krótkich tras. Porównanie pokazuje koszt uzyskania jakości, a zamknięcie drogi sprawdza reakcję na zmianę problemu. ACO może znaleźć bardzo dobry wynik, lecz ocena wymaga punktu odniesienia, określonego budżetu i wielu prób. Właśnie te zależności możemy badać w naszym laboratorium.')

    page(d, 'Pytania które mogą pojawić się po pokazie')
    questions = [
        ('Czy ACO zawsze znajduje optimum', 'Nie ma takiej gwarancji przy skończonej liczbie prób. W małym przykładzie możemy potwierdzić wynik przeglądem zupełnym; na większej mapie mówimy o najlepszym znalezionym wyniku.'),
        ('Dlaczego wybór mrówki jest losowy', 'Losowanie pozwala próbować różnych tras. Feromon i odległość zmieniają szanse, ale nie narzucają zawsze tego samego kroku.'),
        ('Po co parowanie feromonu', 'Osłabia wpływ wcześniejszych wyborów i ogranicza trwałą dominację starych śladów. Wartość ρ reguluje szybkość tego procesu.'),
        ('Dlaczego 2 opt zaczyna od najbliższego sąsiada', '2-opt ulepsza gotową trasę, więc potrzebuje punktu startowego. Taki wybór jest prosty i jawny; wynik zależy także od tej trasy początkowej.'),
        ('Czy wyścig jest porównaniem równych budżetów', 'Nie. To porównanie wskazanych metod: ACO ma 100 iteracji, najbliższy sąsiad jeden przebieg, a 2-opt pracuje do braku lokalnej poprawy. Czasy mierzymy osobno.'),
        ('Czy czas na wykresie obejmuje animację', 'Nie. Zliczamy czas pracy metody. Oczekiwanie na następny krok prezentacji, rysowanie i tworzenie wykresów nie wchodzą do tej miary.'),
        ('Czy pierwsze obejście oznacza najlepszą trasę', 'Nie. Oznacza pierwszy kompletny objazd bez zamkniętej krawędzi. Dalsze iteracje mogą poprawić jego długość.'),
        ('Czy zachowany feromon zawsze pomaga po blokadzie', 'Nie. Może też utrwalać wcześniejsze preferencje. W skrypcie badawczym porównujemy kontynuację i start od zera, z osobnym warunkiem jakości.'),
        ('Co oznacza brak znalezionej trasy', 'Heurystyka mogła utknąć albo nie znaleźć dobrego porządku. Nie dowodzi to braku cyklu. Dla małych map może go rozstrzygnąć przegląd zupełny.'),
        ('Jak sprawdzono poprawność programu', '18 testów bada zachowanie modelu; osobny skrypt sprawdza zdarzenia Pygame i eksport. Dodatkowo uruchomiono zestaw eksperymentów dla 3–100 punktów.')]
    for question, answer in questions:
        h2(d, question)
        p = para(d, answer)
        p.paragraph_format.space_after = Pt(3)
    h2(d, 'Gdy zabraknie czasu lub zawiedzie pokaz')
    para(d, 'Otwórz zapisane podsumowanie wyścigu i blokady. Wyjaśnij na nich cel, dwie miary porównania i różnicę między pierwszym obejściem a dalszą poprawą. Nie obiecuj konkretnego czasu animacji ani wyniku losowego uruchomienia. Pełna dokumentacja zawiera źródła i dokładne warunki obu przykładów.')
    path = OUT / 'Scenariusz_prezentacji_ACO_TSP.docx'
    d.save(path)
    return path


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    # Wyodrębnienie paneli poprawia czytelność w dokumencie; pełne zrzuty pozostają w wyniki/podglad.
    with Image.open(ROOT / 'wyniki/podglad/sledzenie.png') as image:
        image.crop((24, 573, 465, 811)).save(ASSETS / 'sledzona_mrowka.png')
    with Image.open(ROOT / 'wyniki/podglad/blokada_szukamy.png') as image:
        image.crop((24, 741, 977, 808)).save(ASSETS / 'baner_blokady.png')
    for src, name in [(RACE_DIR / 'dane.json', 'dane_wyscigu.json'),
                      (CLOSURE_DIR / 'dane.json', 'dane_blokady.json')]:
        shutil.copyfile(src, ASSETS / name)
    for path in (build_main(), build_talk()):
        print(path)


if __name__ == '__main__':
    main()
