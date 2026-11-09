// Generuje dokumentację projektu w formacie Word.
// Użycie: node dokumentacja.js <katalog_projektu>
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, WidthType, ShadingType, BorderStyle, LevelFormat,
  TableOfContents, Footer, PageNumber, PageBreak,
} = require('docx');

const PROJ = process.argv[2];
const IMG = path.join(PROJ, 'dokumentacja', 'obrazy');
const RES = path.join(PROJ, 'wyniki');
const OUT = path.join(PROJ, 'dokumentacja', 'Dokumentacja_ACO_TSP.docx');

const FONT = 'Calibri';
const CONTENT_W = 9072; // A4 z marginesami 2,5 cm (DXA)
const MAX_IMG_PX = 600;

// ---------- pomocnicze ----------
let figNo = 0, tabNo = 0;

function runs(text, opts = {}) {
  // **pogrubienie** i *kursywa* w prostym zapisie
  const parts = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|_\{[^}]+\}|\^\{[^}]+\})/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) parts.push(new TextRun({ text: text.slice(last, m.index), ...opts }));
    const t = m[0];
    if (t.startsWith('_{')) parts.push(new TextRun({ text: t.slice(2, -1), subScript: true, ...opts }));
    else if (t.startsWith('^{')) parts.push(new TextRun({ text: t.slice(2, -1), superScript: true, ...opts }));
    else if (t.startsWith('**')) parts.push(new TextRun({ text: t.slice(2, -2), bold: true, ...opts }));
    else parts.push(new TextRun({ text: t.slice(1, -1), italics: true, ...opts }));
    last = m.index + t.length;
  }
  if (last < text.length) parts.push(new TextRun({ text: text.slice(last), ...opts }));
  return parts;
}

const P = (text, extra = {}) => new Paragraph({
  children: runs(text), alignment: AlignmentType.JUSTIFIED, spacing: { after: 120, line: 288 }, ...extra,
});
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)], pageBreakBefore: true });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const bullet = (text) => new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: runs(text), spacing: { after: 60, line: 276 } });
const numbered = (text, ref = 'steps') => new Paragraph({ numbering: { reference: ref, level: 0 }, children: runs(text), spacing: { after: 60, line: 276 } });

function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20), data: b };
}

function image(name, { widthPx = MAX_IMG_PX, dpi = null } = {}) {
  const { w, h, data } = pngSize(path.join(IMG, name));
  let width = dpi ? Math.round(w * 96 / dpi) : widthPx;
  width = Math.min(width, MAX_IMG_PX);
  const height = Math.round(width * h / w);
  return new ImageRun({ type: 'png', data, transformation: { width, height },
    altText: { title: name, description: name, name } });
}

function figure(name, caption, opts) {
  figNo++;
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 }, keepNext: true,
      children: [image(name, opts)] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
      children: [new TextRun({ text: `Rysunek ${figNo}. `, bold: true, size: 20 }), new TextRun({ text: caption, italics: true, size: 20 })] }),
  ];
}

function figureFrom(dir, name, caption, opts) {
  const tmp = path.join(IMG, name);
  fs.copyFileSync(path.join(dir, name), tmp);
  return figure(name, caption, opts);
}

function formula(name, no) {
  // wzór wyśrodkowany, numer przy prawym marginesie (tabela bez obramowania)
  const none = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };
  const borders = { top: none, bottom: none, left: none, right: none };
  const widths = [800, CONTENT_W - 1600, 800];
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: widths,
    borders: { ...borders, insideHorizontal: none, insideVertical: none },
    rows: [new TableRow({ children: [
      new TableCell({ borders, width: { size: widths[0], type: WidthType.DXA }, children: [new Paragraph('')] }),
      new TableCell({ borders, width: { size: widths[1], type: WidthType.DXA }, verticalAlign: 'center',
        children: [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 80 }, children: [image(name, { dpi: 200 })] })] }),
      new TableCell({ borders, width: { size: widths[2], type: WidthType.DXA }, verticalAlign: 'center',
        children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun(`(${no})`)] })] }),
    ] })],
  });
}

const border = { style: BorderStyle.SINGLE, size: 4, color: 'A6A6A6' };
const cellBorders = { top: border, bottom: border, left: border, right: border };

function table(caption, header, rows, widths, { align = [] } = {}) {
  tabNo++;
  const total = widths.reduce((a, b) => a + b, 0);
  const mkCell = (text, i, isHead) => new TableCell({
    borders: cellBorders,
    width: { size: widths[i], type: WidthType.DXA },
    shading: isHead ? { fill: 'D9E2F3', type: ShadingType.CLEAR, color: 'auto' } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({
      alignment: isHead ? AlignmentType.CENTER : (align[i] || AlignmentType.LEFT),
      children: runs(String(text), { size: 20, bold: isHead || undefined }),
    })],
  });
  return [
    new Paragraph({ spacing: { before: 160, after: 80 }, keepNext: true,
      children: [new TextRun({ text: `Tabela ${tabNo}. `, bold: true, size: 20 }), new TextRun({ text: caption, italics: true, size: 20 })] }),
    new Table({
      width: { size: total, type: WidthType.DXA }, columnWidths: widths,
      rows: [
        new TableRow({ tableHeader: true, children: header.map((h, i) => mkCell(h, i, true)) }),
        ...rows.map((r) => new TableRow({ children: r.map((c, i) => mkCell(c, i, false)) })),
      ],
    }),
    new Paragraph({ spacing: { after: 120 }, children: [] }),
  ];
}

function code(lines) {
  return lines.map((l, k) => new Paragraph({
    shading: { fill: 'F2F2F2', type: ShadingType.CLEAR, color: 'auto' },
    spacing: { after: 0, line: 240 },
    keepLines: true, keepNext: k < lines.length - 1,
    indent: { left: 200, right: 200 },
    children: [new TextRun({ text: l.length ? l : ' ', font: 'Consolas', size: 18 })],
  }));
}

function readCsv(name) {
  const lines = fs.readFileSync(path.join(RES, name), 'utf8').trim().split(/\r?\n/);
  return lines.slice(1).map((l) => l.split(';'));
}

const fmtNum = (v, d = 2) => Number(v).toFixed(d).replace('.', ',');
const fmtMs = (v) => {
  const x = Number(v);
  if (x < 1) return fmtNum(x, 3);
  if (x < 100) return fmtNum(x, 1);
  return fmtNum(x, 0);
};

// ---------- tabele wyników ----------
function pivot(rows, algos) {
  const by = {};
  for (const [n, a, gap, t] of rows) (by[n] ||= {})[a] = { gap, t };
  return Object.keys(by).map(Number).sort((a, b) => a - b).map((n) => [String(n), ...algos.flatMap((a) => {
    const r = by[n][a];
    return r ? [fmtNum(r.gap, 2), fmtMs(r.t)] : ['–', '–'];
  })]);
}

const small = readCsv('wyniki_male.csv');
const large = readCsv('wyniki_duze.csv');
const conv = readCsv('wyniki_zbieznosc.csv');
const block = readCsv('wyniki_blokada.csv');
const smallAlgos = ['ACO', 'Najbliższy sąsiad', '2-opt', 'Przegląd zupełny'];
const largeAlgos = ['ACO', 'Najbliższy sąsiad', '2-opt'];
const bf10 = small.find((r) => r[0] === '10' && r[1] === 'Przegląd zupełny');
const bf9 = small.find((r) => r[0] === '9' && r[1] === 'Przegląd zupełny');
const blockVal = (k) => fmtNum(block[k][1], 1);
const acoMs = (n) => Number(small.find((r) => r[0] === n && r[1] === 'ACO')[3]);
const acoMsLarge = (n) => Number(large.find((r) => r[0] === n && r[1] === 'ACO')[3]);

// ---------- treść ----------
const C = AlignmentType.CENTER;
const titlePage = [
  new Paragraph({ alignment: C, spacing: { before: 600, after: 120 }, children: [new TextRun({ text: '[Nazwa uczelni]', size: 28 })] }),
  new Paragraph({ alignment: C, spacing: { after: 1400 }, children: [new TextRun({ text: '[Wydział / kierunek]', size: 24 })] }),
  new Paragraph({ alignment: C, spacing: { after: 200 }, children: [new TextRun({ text: 'Algorytmy inteligentne inspirowane naturą', size: 28, color: '595959' })] }),
  new Paragraph({ alignment: C, spacing: { after: 200 }, children: [new TextRun({ text: 'Dokumentacja projektu', size: 24, color: '595959' })] }),
  new Paragraph({ alignment: C, spacing: { before: 400, after: 1600 }, children: [new TextRun({ text: 'Zastosowanie algorytmu mrówkowego (ACO) do rozwiązania problemu komiwojażera (TSP)', size: 40, bold: true, color: '1F3864' })] }),
  ...[['Autorzy:', '[imię i nazwisko], [imię i nazwisko]'], ['Grupa:', '[numer grupy]'], ['Prowadzący:', '[tytuł, imię i nazwisko]'], ['Wersja dokumentu:', '2.0 – szczegółowy opis projektu na drugie zajęcia'], ['Data:', 'listopad 2026']]
    .map(([k, v]) => new Paragraph({ alignment: C, spacing: { after: 80 }, children: [new TextRun({ text: k + ' ', bold: true }), new TextRun(v)] })),
  new Paragraph({ children: [new PageBreak()] }),
  new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun('Spis treści')] }),
  new TableOfContents('Spis treści', { hyperlink: true, headingStyleRange: '1-2' }),
];

const s1 = [
  H1('1. Wprowadzenie'),
  H2('1.1. Cel projektu'),
  P('Celem projektu jest zbadanie, jak algorytm mrówkowy (ang. *Ant Colony Optimization*, ACO) radzi sobie z problemem komiwojażera (ang. *Travelling Salesman Problem*, TSP), oraz porównanie go z metodą dokładną i dwiema klasycznymi heurystykami. Problem przedstawiono w formie bliskiej oryginalnej inspiracji: na planszy znajduje się mrowisko oraz punkty z pożywieniem, a kolonia mrówek szuka najkrótszej trasy, która zaczyna się w mrowisku, odwiedza każdy punkt z pożywieniem dokładnie raz i wraca do mrowiska.'),
  P('Działanie algorytmu jest pokazane w interaktywnej aplikacji: widać, jak w kolejnych iteracjach na ścieżkach odkłada się feromon, jak słabsze ścieżki stopniowo zanikają i jak kolonia skupia się na coraz krótszej trasie.'),
  H2('1.2. Uzasadnienie wyboru tematu'),
  bullet('**Problem jest trudny obliczeniowo.** Problem komiwojażera jest NP-trudny, a liczba możliwych tras rośnie jak n!/2. Już przy kilkunastu punktach przegląd zupełny przestaje być wykonalny, więc potrzebne są metody przybliżone – dokładnie ten obszar, w którym stosuje się algorytmy inspirowane naturą.'),
  bullet('**Problem ma praktyczne zastosowania.** Do TSP sprowadza się planowanie tras dostaw i odbioru odpadów, kolejność wiercenia otworów w płytkach drukowanych, ruch głowicy maszyn CNC czy kolejność zadań w produkcji.'),
  bullet('**Algorytm mrówkowy powstał właśnie dla TSP.** M. Dorigo zaproponował go w 1992 roku i pierwsze wyniki pokazał na problemie komiwojażera. TSP jest do dziś podstawowym problemem testowym dla nowych wariantów ACO, więc łatwo porównać własne wyniki z literaturą.'),
  bullet('**Temat dobrze się wizualizuje.** Plansza z mrowiskiem i pożywieniem odpowiada biologicznej inspiracji algorytmu, a feromon na ścieżkach można rysować bezpośrednio. Dzięki temu działanie algorytmu – w tym wpływ parametrów α, β i ρ – widać, a nie tylko odczytuje się je z liczb.'),
  bullet('**Wyniki można rzetelnie ocenić.** Dla małych plansz znamy trasę optymalną (przegląd zupełny), a dla większych mamy klasyczne heurystyki (najbliższy sąsiad, 2-opt), więc jakość i czas działania ACO da się zmierzyć.'),
  H2('1.3. Zakres prac'),
  bullet('implementacja algorytmu mrówkowego (Ant System ze strategią elitarną),'),
  bullet('implementacja algorytmów porównawczych: przeglądu zupełnego, najbliższego sąsiada i 2-opt,'),
  bullet('aplikacja w bibliotece Pygame do wizualizacji i ręcznego ustawiania planszy, z panelem wzorów, podglądem prawdopodobieństw wyboru i animacją mrówek,'),
  bullet('eksperymenty: długość trasy i czas obliczeń dla rosnącej liczby punktów, wpływ parametrów ACO,'),
  bullet('rozszerzenie opcjonalne: zachowanie kolonii po zablokowaniu jednej ze ścieżek.'),
  H2('1.4. Stan prac'),
  P('Niniejsza wersja dokumentu opisuje projekt na drugie zajęcia. Wszystkie elementy z punktu 1.3 działają. W porównaniu z wersją wstępną dodano klasyfikację algorytmu i przegląd wyników z literatury (rozdział 3), a aplikację rozbudowano o elementy pokazujące, jak działają wzory algorytmu: panel ze wzorami i bieżącymi parametrami, podgląd prawdopodobieństw wyboru kolejnego punktu oraz animację mrówek (rozdział 6). Wstępne wyniki eksperymentów przedstawiono w rozdziale 7, a plan dalszych prac w rozdziale 8.'),
];

const s2 = [
  H1('2. Opis problemu'),
  H2('2.1. Problem komiwojażera'),
  P('Dany jest zbiór n + 1 punktów: mrowisko (punkt 0) oraz n punktów z pożywieniem (1, …, n). Dla każdej pary punktów i, j znana jest odległość d_{ij}. Szukamy permutacji π punktów, która zaczyna się w mrowisku i minimalizuje długość zamkniętej trasy:'),
  formula('wzor_tsp.png', 1),
  P('Odległości są symetryczne (d_{ij} = d_{ji}), więc każdą trasę można przejść w dwóch kierunkach. Przy ustalonym punkcie startowym liczba różnych tras wynosi **n!/2**. Dla 10 punktów pożywienia to 1 814 400 tras, a dla 20 punktów już około 1,2·10¹⁸. Problem komiwojażera jest NP-trudny: nie jest znany algorytm, który zawsze znajduje trasę optymalną w czasie wielomianowym. Dlatego dla większej liczby punktów stosuje się heurystyki i metaheurystyki, takie jak algorytm mrówkowy.'),
  H2('2.2. Model planszy'),
  bullet('Plansza ma wymiary 900 × 760 pikseli; w eksperymentach punkty losuje się w kwadracie 100 × 100.'),
  bullet('Odległość między punktami jest odległością euklidesową.'),
  bullet('Mrowisko jest zawsze punktem startowym i końcowym trasy; można je przesuwać, ale nie można go usunąć.'),
  bullet('Ścieżkę między dwoma punktami można zablokować. Zablokowana krawędź dostaje bardzo dużą długość (10⁶), dlatego każdy algorytm jej unika, a trasa, która mimo to z niej korzysta, jest od razu widoczna jako bardzo długa.'),
];

const s3 = [
  H1('3. Algorytm mrówkowy'),
  H2('3.1. Klasyfikacja algorytmu'),
  P('Algorytm mrówkowy należy do **algorytmów inspirowanych naturą**, a w ich obrębie do grupy **inteligencji roju** (ang. *swarm intelligence*). Algorytmy tej grupy wykorzystują populację prostych agentów, z których żaden nie zna całego problemu, a dobre rozwiązanie wyłania się z ich lokalnych działań i pośredniej komunikacji. Jest to **metaheurystyka populacyjna i konstrukcyjna**: każda mrówka buduje kompletne rozwiązanie od zera, krok po kroku, a „pamięcią” całej kolonii jest macierz feromonu.'),
  ...code([
    'Algorytmy inspirowane naturą',
    '├── algorytmy ewolucyjne (algorytm genetyczny, strategie ewolucyjne, ...)',
    '├── inteligencja roju                         ◄ ta grupa',
    '│    ├── optymalizacja rojem cząstek (PSO)',
    '│    ├── sztuczna kolonia pszczół (ABC)',
    '│    └── optymalizacja kolonią mrówek (ACO)   ◄ ta rodzina',
    '│         ├── Ant System (AS)',
    '│         ├── Elitist Ant System (EAS)        ◄ wariant użyty w projekcie',
    '│         ├── Rank-based Ant System (ASrank)',
    '│         ├── Ant Colony System (ACS)',
    '│         └── MAX–MIN Ant System (MMAS)',
    '└── inne (wyżarzanie symulowane, systemy immunologiczne, ...)',
  ]),
  new Paragraph({ spacing: { after: 120 }, children: [] }),
  ...table('Najważniejsze warianty algorytmu mrówkowego dla TSP',
    ['Wariant', 'Autorzy, rok', 'Czym się wyróżnia'],
    [
      ['Ant System (AS)', 'Dorigo, Maniezzo, Colorni 1991/1996', 'pierwsza wersja: wszystkie mrówki odkładają feromon proporcjonalny do 1/L_{k}'],
      ['Elitist AS (EAS)', 'Dorigo 1992, Dorigo i in. 1996', 'AS + dodatkowy feromon na najlepszej dotąd trasie (waga e) – szybsza zbieżność'],
      ['Rank-based AS', 'Bullnheimer, Hartl, Strauss 1999', 'feromon odkładają tylko najlepsze mrówki, z wagą zależną od miejsca w rankingu'],
      ['Ant Colony System (ACS)', 'Dorigo, Gambardella 1997', 'reguła pseudolosowa, lokalna aktualizacja feromonu w trakcie budowy trasy, feromon odkłada tylko najlepsza mrówka'],
      ['MAX–MIN AS (MMAS)', 'Stützle, Hoos 2000', 'feromon ograniczony z dołu i z góry [τ_{min}, τ_{max}], odkłada go tylko najlepsza mrówka – mniejsze ryzyko stagnacji'],
    ], [2200, 2600, 4272]),
  P('**Wariant użyty w projekcie** to Ant System ze strategią elitarną (EAS), uzupełniony o dolne ograniczenie feromonu (zapożyczone z MMAS). Wybraliśmy go, ponieważ jest najbliższy oryginalnej idei – feromon odkładają wszystkie mrówki, więc na planszy widać ślady całej kolonii, a nie tylko jednej trasy – a przy tym dzięki wzmocnieniu najlepszej trasy zbiega szybciej niż podstawowy AS. Proste reguły ułatwiają też pokazanie wzorów na żywo w aplikacji. Warianty ACS i MMAS planujemy wykorzystać w dalszej części projektu jako punkt odniesienia.'),
  H2('3.2. Inspiracja biologiczna'),
  P('Mrówki komunikują się pośrednio, przez zmiany w otoczeniu (tzw. stygmergia). Idąca mrówka zostawia na podłożu feromon, a inne mrówki chętniej wybierają ścieżki, na których feromonu jest więcej. Na krótszej ścieżce mrówki szybciej wracają do mrowiska, więc w tym samym czasie przechodzi nią więcej mrówek i gromadzi się na niej więcej feromonu. Feromon z czasem paruje, przez co rzadziej używane, dłuższe ścieżki są stopniowo porzucane. W doświadczeniu z podwójnym mostkiem (Goss i in., 1989) kolonia mrówek argentyńskich w ten sposób wybierała krótszą z dwóch dróg do pożywienia.'),
  P('Algorytm mrówkowy zaproponowany przez M. Dorigo przenosi ten mechanizm do optymalizacji: sztuczne mrówki budują rozwiązania krok po kroku, korzystając z feromonu odłożonego przez poprzednie pokolenia, a po każdej iteracji feromon jest aktualizowany zależnie od jakości znalezionych tras.'),
  H2('3.3. Budowa trasy przez mrówkę'),
  P('Każda mrówka zaczyna w mrowisku. Będąc w punkcie i, wybiera kolejny punkt j spośród jeszcze nieodwiedzonych (zbiór N_{i}^{k}) z prawdopodobieństwem:'),
  formula('wzor_p.png', 2),
  P('gdzie τ_{ij} to ilość feromonu na krawędzi (i, j), η_{ij} to „widoczność”, czyli odwrotność odległości, a α i β określają, jak mocno mrówka kieruje się feromonem, a jak mocno odległością. Wybór realizowany jest metodą ruletki. Po odwiedzeniu wszystkich punktów mrówka wraca do mrowiska.'),
  H2('3.4. Aktualizacja feromonu'),
  P('Po zbudowaniu tras przez wszystkie m mrówek feromon najpierw paruje, a następnie każda mrówka odkłada feromon na krawędziach swojej trasy. Dodatkowo wzmacniana jest najlepsza dotąd znaleziona trasa (strategia elitarna):'),
  formula('wzor_tau.png', 3),
  formula('wzor_dtau.png', 4),
  P('Δτ_{ij}^{k} jest niezerowe tylko dla krawędzi, którymi przeszła mrówka k; L_{k} to długość jej trasy, a Q to stała. Im krótsza trasa, tym więcej feromonu dostają jej krawędzie. Δτ_{ij}^{best} liczone jest w ten sam sposób dla najlepszej dotąd trasy, a e jest wagą wzmocnienia elitarnego.'),
  P('**Przykład liczbowy.** Mrówka stoi w mrowisku, a feromon jest jeszcze wszędzie równy (τ = τ0). Najbliższe punkty leżą w odległości 73 i 79. Przy β = 3 ich wagi mają się do siebie jak (79/73)³ ≈ 1,27, więc bliższy punkt dostaje około 51% szans, a dalszy około 40% (pozostałe, odległe punkty dzielą resztę). Po 8 iteracjach na krawędzi do bliższego punktu jest już około 3 razy więcej feromonu niż na krawędzi do dalszego i proporcja zmienia się na 79% do 19%. Dokładnie te liczby pokazuje aplikacja w trybie „Wybór” (rysunki 5 i 6 w rozdziale 6.3).'),
  H2('3.5. Pseudokod'),
  ...code([
    'wejście: macierz odległości d, parametry m, α, β, ρ, Q, e, liczba iteracji T',
    'τ ← τ0 dla wszystkich krawędzi,  τ0 = 1 / (n · L_NN)',
    'najlepsza ← brak',
    'powtarzaj T razy:',
    '    dla każdej mrówki k = 1..m:',
    '        trasa_k ← [0]                      # start w mrowisku',
    '        dopóki są nieodwiedzone punkty:',
    '            wybierz j z prawdopodobieństwem p_ij  (wzór 2)',
    '            dodaj j do trasa_k',
    '        L_k ← długość(trasa_k)             # z powrotem do mrowiska',
    '        jeśli L_k < długość(najlepsza): najlepsza ← trasa_k',
    '    τ ← (1 − ρ) · τ                        # parowanie',
    '    dla każdej mrówki k: dodaj Q / L_k na krawędziach trasa_k',
    '    dodaj e · Q / L_best na krawędziach najlepszej trasy',
    '    τ ← max(τ, τ_min)                      # żadna ścieżka nie znika całkiem',
    'zwróć najlepsza',
  ]),
  new Paragraph({ spacing: { after: 120 }, children: [] }),
  H2('3.6. Parametry algorytmu'),
  ...table('Parametry algorytmu mrówkowego',
    ['Symbol', 'Znaczenie', 'Domyślnie', 'Zakres w aplikacji'],
    [
      ['m', 'liczba mrówek w jednej iteracji', '20', '5–100'],
      ['α', 'waga feromonu w regule wyboru', '1,0', '0–5'],
      ['β', 'waga odległości (widoczności)', '3,0', '0–10'],
      ['ρ', 'współczynnik parowania feromonu', '0,3', '0,01–0,9'],
      ['Q', 'stała ilości odkładanego feromonu', '1', 'stała'],
      ['e', 'waga wzmocnienia najlepszej trasy', '1', 'stała'],
      ['T', 'liczba iteracji', '100 (w eksperymentach)', 'bez limitu (Start/Pauza)'],
    ], [1000, 3972, 1900, 2200], { align: [AlignmentType.CENTER, null, AlignmentType.CENTER, AlignmentType.CENTER] }),
  H2('3.7. Szczegóły implementacji'),
  bullet('**Feromon początkowy** τ0 = 1/(n · L_{NN}), gdzie L_{NN} to długość trasy najbliższego sąsiada; dzięki temu skala feromonu nie zależy od wielkości planszy.'),
  bullet('**Dolne ograniczenie feromonu** τ_{min} = τ0 · 10⁻³ zapobiega całkowitemu zanikowi ścieżek. Jest to szczególnie ważne po zablokowaniu ścieżki, gdy kolonia musi znaleźć objazd.'),
  bullet('**Wagi wyboru** [τ]^{α}·[η]^{β} obliczane są raz na iterację dla całej macierzy (biblioteka NumPy), a mrówka losuje kolejny punkt przez sumę skumulowaną wag.'),
  bullet('**Praca krokowa**: klasa AntColony udostępnia metodę iterate(), która wykonuje jedną iterację. Iteracja jest podzielona na dwa etapy – construct_tours() (mrówki budują trasy, feromon się nie zmienia) i update_pheromone(tours) (parowanie i odkładanie feromonu). Dzięki temu aplikacja może między tymi etapami pokazać animację mrówek idących po swoich trasach.'),
  bullet('**Podgląd reguły wyboru**: metoda probabilities(i, visited) zwraca wektor prawdopodobieństw p_{ij} liczony dokładnie tym samym wzorem, którego używają mrówki. Aplikacja rysuje go na planszy w trybie „Wybór”.'),
  H2('3.8. Dotychczasowe wyniki w literaturze'),
  bullet('**Ant System** (Dorigo, Maniezzo, Colorni 1996) na małych instancjach, np. Oliver30 (30 miast), znajdował najlepsze znane trasy i dorównywał innym metodom ogólnego przeznaczenia. Na większych instancjach ustępował jednak wyspecjalizowanym algorytmom dla TSP. W tej samej pracy pokazano, że dodanie mrówek elitarnych (EAS) poprawia wyniki, o ile ich liczba nie jest zbyt duża.'),
  bullet('**Ant Colony System** (Dorigo, Gambardella 1997) na losowych instancjach z 50 miastami oraz instancjach testowych Oliver30, Eil50, Eil75 i KroA100 dawał wyniki lepsze lub równe algorytmowi genetycznemu, programowaniu ewolucyjnemu, wyżarzaniu symulowanemu i sieciom samoorganizującym się. W połączeniu z lokalnym przeszukiwaniem 3-opt był konkurencyjny z najlepszymi wówczas algorytmami genetycznymi na instancjach z biblioteki TSPLIB liczących nawet ponad tysiąc miast.'),
  bullet('**MAX–MIN Ant System** (Stützle, Hoos 2000) przez ograniczenie feromonu do przedziału [τ_{min}, τ_{max}] ograniczył problem stagnacji. Na instancjach TSPLIB uzyskiwał lepsze wyniki niż Ant System i jego wcześniejsze rozszerzenia, a z lokalnym przeszukiwaniem należy do najskuteczniejszych wariantów ACO dla TSP.'),
  bullet('**Stan wiedzy** (Dorigo, Stützle 2004): algorytmy mrówkowe z lokalnym przeszukiwaniem dają trasy bardzo bliskie optymalnym, ale dla samego TSP najlepsze pozostają metody wyspecjalizowane – heurystyka Lina–Kernighana oraz metody dokładne. Program Concorde (Applegate i in.) rozwiązał dokładnie instancję z 85 900 miastami. Siłą ACO jest raczej uniwersalność: ten sam schemat stosuje się do problemów trasowania pojazdów, przydziału czy harmonogramowania, a także do problemów zmieniających się w czasie, jak zablokowanie ścieżki w naszym rozszerzeniu.'),
  P('Wyniki z literatury wskazują dwa kierunki, które sprawdzamy w projekcie: połączenie ACO z lokalnym przeszukiwaniem (2-opt) oraz ograniczanie feromonu w celu uniknięcia stagnacji. Nasze wstępne wyniki (rozdział 7) są z literaturą zgodne – podstawowy wariant bez lokalnego przeszukiwania jest porównywalny z 2-opt, ale wyraźnie od niego wolniejszy.'),
];

const s4 = [
  H1('4. Algorytmy porównawcze'),
  H2('4.1. Przegląd zupełny (brute force)'),
  P('Algorytm sprawdza wszystkie permutacje punktów pożywienia i wybiera najkrótszą trasę, więc zawsze daje wynik optymalny. Implementacja pomija trasy będące odwróceniem już sprawdzonych (pierwszy odwiedzony punkt musi mieć mniejszy numer niż ostatni) i przerywa liczenie trasy, gdy jej częściowa długość przekroczy najlepszy dotąd wynik. Mimo tych usprawnień złożoność pozostaje rzędu O(n!), dlatego w aplikacji algorytm jest dostępny tylko do 10 punktów pożywienia.'),
  H2('4.2. Algorytm najbliższego sąsiada'),
  P('Prosta heurystyka zachłanna: startując z mrowiska, zawsze idziemy do najbliższego jeszcze nieodwiedzonego punktu, a na końcu wracamy do mrowiska. Złożoność O(n²). Algorytm jest bardzo szybki, ale nie „patrzy w przyszłość”, więc pod koniec trasy często musi wykonać długie przejścia.'),
  H2('4.3. Algorytm 2-opt'),
  P('Algorytm lokalnego ulepszania trasy (Croes, 1958). Startuje od trasy najbliższego sąsiada i sprawdza pary krawędzi (a, b) oraz (c, d). Jeśli zastąpienie ich krawędziami (a, c) i (b, d) skraca trasę, odwraca fragment trasy między b i c. Zamiany wykonuje się, dopóki żadna nie daje poprawy. Wynikowa trasa nie ma przecinających się odcinków. Jedno przejście kosztuje O(n²).'),
  H2('4.4. Zestawienie'),
  ...table('Porównanie cech zastosowanych algorytmów',
    ['Algorytm', 'Rodzaj', 'Złożoność', 'Optimum'],
    [
      ['Przegląd zupełny', 'dokładny', 'O(n!)', 'zawsze'],
      ['Najbliższy sąsiad', 'heurystyka konstrukcyjna (zachłanna)', 'O(n²)', 'nie'],
      ['2-opt', 'przeszukiwanie lokalne', 'O(n²) na przejście', 'nie (optimum lokalne)'],
      ['Algorytm mrówkowy', 'metaheurystyka populacyjna (inteligencja roju)', 'O(T · m · n²)', 'nie (zwykle blisko)'],
    ], [2000, 3272, 1900, 1900]),
];

const s5 = [
  H1('5. Implementacja'),
  H2('5.1. Technologie'),
  bullet('**Python 3.13** – język programowania (projekt działa od wersji 3.10),'),
  bullet('**Pygame 2.6** – interfejs graficzny i animacja,'),
  bullet('**NumPy** – obliczenia na macierzach odległości i feromonu,'),
  bullet('**Matplotlib** – wykresy z wynikami eksperymentów.'),
  H2('5.2. Struktura projektu'),
  ...table('Pliki projektu',
    ['Plik', 'Zawartość'],
    [
      ['algorytmy.py', 'macierz odległości, długość trasy, przegląd zupełny, najbliższy sąsiad, 2-opt, klasa AntColony'],
      ['aplikacja.py', 'aplikacja Pygame: plansza, panel sterowania, rysowanie feromonu i tras, panel wzorów, prawdopodobieństwa wyboru, animacja mrówek, porównanie algorytmów, blokowanie ścieżek'],
      ['porownanie.py', 'eksperymenty; zapisuje tabele CSV i wykresy PNG do katalogu wyniki/'],
      ['uruchom.bat', 'uruchomienie aplikacji dwuklikiem w systemie Windows; przy pierwszym uruchomieniu tworzy środowisko wirtualne .venv i instaluje biblioteki'],
      ['README.md, requirements.txt', 'instrukcja uruchomienia i lista wymaganych bibliotek'],
      ['dokumentacja/', 'niniejszy dokument, prezentacja, rysunki oraz skrypty generujące (narzedzia/)'],
    ], [2600, 6472]),
  H2('5.3. Najważniejsze elementy kodu'),
  P('Wszystkie algorytmy działają na tej samej macierzy odległości tworzonej funkcją distance_matrix(points, blocked), która od razu uwzględnia zablokowane ścieżki. Trasa jest listą numerów punktów zaczynającą się od 0 (mrowisko); powrót do mrowiska jest domyślny.'),
  ...table('Interfejs klasy AntColony',
    ['Element', 'Opis'],
    [
      ['AntColony(dist, n_ants, alpha, beta, rho, q, elite, seed)', 'tworzy kolonię i inicjalizuje feromon wartością τ0'],
      ['iterate()', 'jedna iteracja: budowa tras, parowanie, odłożenie feromonu, aktualizacja najlepszej trasy'],
      ['construct_tours()', 'etap 1 iteracji: każda z m mrówek buduje trasę; zwraca listę tras'],
      ['update_pheromone(tours)', 'etap 2 iteracji: parowanie, odłożenie feromonu, wzmocnienie najlepszej trasy'],
      ['probabilities(i, visited)', 'prawdopodobieństwa p_{ij} wyboru kolejnego punktu przez mrówkę stojącą w i (wzór 2)'],
      ['run(T)', 'wykonuje T iteracji i zwraca najlepszą trasę'],
      ['set_distances(dist)', 'podmienia macierz odległości bez kasowania feromonu (używane po zablokowaniu ścieżki)'],
      ['tau, best_tour, best_length, history', 'macierz feromonu, najlepsza trasa, jej długość i historia długości w kolejnych iteracjach'],
    ], [3600, 5472]),
  P('Aplikacja (klasa App) w każdej klatce obsługuje zdarzenia myszy i klawiatury, wykonuje zadaną liczbę iteracji ACO (gdy algorytm jest uruchomiony) i rysuje planszę. Grubość i przezroczystość linii między punktami są proporcjonalne do ilości feromonu na danej krawędzi, a najlepsza znaleziona trasa jest rysowana na czerwono. Parametry zmienione suwakami trafiają od razu do działającej kolonii, więc ich wpływ widać bez restartu.'),
];

const s6 = [
  H1('6. Interfejs użytkownika – instrukcja obsługi'),
  H2('6.1. Okno aplikacji i sterowanie'),
  P('Aplikację uruchamia się dwuklikiem na pliku **uruchom.bat** albo poleceniem **python aplikacja.py** (opcja **--okno** uruchamia ją w oknie zamiast na pełnym ekranie). Okno składa się z planszy (po lewej) i panelu sterowania (po prawej). Na starcie losowanych jest 15 punktów pożywienia, a mrowisko znajduje się na środku planszy.'),
  ...figure('gui_start.png', 'Okno aplikacji zaraz po uruchomieniu: mrowisko (brązowe), punkty z pożywieniem (zielone) i panel sterowania'),
  ...table('Sterowanie aplikacją',
    ['Akcja', 'Działanie'],
    [
      ['lewy przycisk myszy na pustym miejscu', 'dodaje punkt z pożywieniem'],
      ['przeciągnięcie punktu', 'przesuwa punkt lub mrowisko'],
      ['prawy przycisk myszy na punkcie', 'usuwa punkt (mrowiska nie można usunąć)'],
      ['Spacja / „Start”', 'uruchamia lub zatrzymuje algorytm mrówkowy'],
      ['S / „Krok”', 'wykonuje jedną iterację'],
      ['R / „Losuj punkty”', 'losuje tyle punktów, ile ustawiono suwakiem'],
      ['C / „Wyczyść”', 'usuwa wszystkie punkty pożywienia'],
      ['„Reset feromonu”', 'zaczyna działanie kolonii od nowa'],
      ['B / „Blokowanie”', 'w tym trybie kliknięcie odcinka blokuje lub odblokowuje ścieżkę'],
      ['P / „Porównaj algorytmy”', 'wyznacza trasy wszystkimi algorytmami i pokazuje tabelę wyników; kliknięcie wiersza rysuje daną trasę'],
      ['„Feromon”', 'włącza lub wyłącza rysowanie śladów feromonu'],
      ['I / „Wzory (I)”', 'pokazuje lub ukrywa panel z grupą algorytmu, użytym wariantem, wzorami i bieżącymi parametrami'],
      ['W / „Wybór (W)”', 'tryb podglądu reguły wyboru: kliknięcie punktu pokazuje prawdopodobieństwa przejścia do pozostałych punktów'],
      ['K / „Kroki (K)”', 'w trybie „Wybór”: najbardziej prawdopodobna trasa mrówki krok po kroku z szansą każdego kroku'],
      ['A / „Mrówki (A)”', 'włącza lub wyłącza animację mrówek przechodzących swoje trasy'],
      ['suwaki', 'liczba losowanych punktów, liczba mrówek, α, β, ρ, prędkość animacji (iteracje na klatkę albo tempo ruchu mrówek)'],
      ['F11 / Esc', 'przełącza pełny ekran i okno / zamyka aplikację'],
    ], [3600, 5472]),
  P('W lewym górnym rogu planszy wyświetlane są: liczba punktów, numer iteracji, długość najlepszej trasy i łączny czas obliczeń algorytmu mrówkowego. W panelu pod suwakami znajduje się wykres długości najlepszej trasy w kolejnych iteracjach.'),
  ...table('Znaczenie elementów planszy',
    ['Element', 'Znaczenie'],
    [
      ['brązowy kopczyk', 'mrowisko – początek i koniec każdej trasy'],
      ['zielone kółka z numerami', 'punkty z pożywieniem'],
      ['fioletowe linie', 'feromon; grubość i nieprzezroczystość linii rosną z ilością feromonu na krawędzi'],
      ['czerwona linia', 'najlepsza trasa znaleziona do tej pory'],
      ['czerwona przerywana linia ze znakiem X', 'zablokowana ścieżka'],
      ['pomarańczowe linie z procentami', 'tryb „Wybór”: prawdopodobieństwo przejścia z zaznaczonego punktu'],
      ['ciemne sylwetki na ścieżkach', 'tryb „Mrówki”: mrówki przechodzące swoje trasy w bieżącej iteracji'],
    ], [3600, 5472]),
  ...figure('gui_iter3.png', 'Stan po 3 iteracjach: feromon (fioletowe linie) jest rozłożony na wielu ścieżkach'),
  ...figure('gui_iter100.png', 'Stan po 100 iteracjach: feromon skupił się na krawędziach krótkiej trasy (czerwona), pozostałe ścieżki prawie zanikły'),
  H2('6.2. Panel „Algorytm i wzory”'),
  P('Klawisz **I** wyświetla na planszy panel, który zbiera w jednym miejscu najważniejsze informacje o algorytmie: grupę (algorytmy inspirowane naturą → inteligencja roju → ACO), użyty wariant (Ant System ze strategią elitarną), regułę wyboru kolejnego punktu, wzór aktualizacji feromonu, objaśnienie symboli oraz bieżące wartości parametrów. Wartości zmieniają się razem z suwakami, więc panel można zostawić otwarty podczas pokazu.'),
  ...figure('gui_wzory.png', 'Panel „Algorytm i wzory” z bieżącymi wartościami parametrów'),
  H2('6.3. Podgląd reguły wyboru (tryb „Wybór”)'),
  P('Tryb **W** pokazuje wzór (2) w działaniu. Po kliknięciu punktu aplikacja zakłada, że stoi w nim mrówka, i dla każdego nieodwiedzonego punktu liczy prawdopodobieństwo p_{ij}. Grubość pomarańczowej linii i etykieta pokazują to prawdopodobieństwo, a tabela obok rozpisuje wzór dla najbardziej prawdopodobnych punktów: odległość, ilość feromonu względem wartości początkowej τ/τ0, iloczyn τ^{α}·η^{β} i wynikowe p_{ij}.'),
  P('Na początku (iteracja 0) feromon jest wszędzie równy, więc o wyborze decyduje tylko odległość – mrówka niemal na pewno pójdzie do jednego z dwóch najbliższych punktów. Po kilku iteracjach feromon zaczyna przeważać: jeden z dwóch podobnie odległych punktów dostaje prawie 80% szans. Przesuwając suwaki α i β, można na żywo zobaczyć, jak zmienia się decyzja mrówki – przy β = 0 wszystkie punkty są niemal równie prawdopodobne, a przy α = 0 feromon przestaje mieć znaczenie.'),
  P('Przycisk **„Kroki (K)”** rozszerza ten podgląd na całą trasę. Mrówka na każdym kroku idzie do punktu o największym prawdopodobieństwie, a na planszy przy kolejnych odcinkach wyświetlane są etykiety z numerem kroku i szansą, np. „1. 79%”, „2. 99%” (rysunek 7). Szansa każdego kroku liczona jest wzorem (2) tylko wśród punktów jeszcze nieodwiedzonych, więc pod koniec trasy rośnie aż do 100% (zostaje jeden punkt, a powrót do mrowiska jest wymuszony). Tabela podaje dla każdego kroku także drugą najlepszą opcję oraz szansę, że mrówka przejdzie dokładnie całą tę trasę (iloczyn szans wszystkich kroków).'),
  ...figure('gui_wybor_start.png', 'Tryb „Wybór” przed pierwszą iteracją: o prawdopodobieństwie decyduje tylko odległość'),
  ...figure('gui_wybor.png', 'Tryb „Wybór” po 8 iteracjach: feromon zwiększył szanse punktu 3 z 51% do 79%'),
  ...figure('gui_kroki.png', 'Przycisk „Kroki”: najbardziej prawdopodobna trasa mrówki z szansą każdego kroku'),
  H2('6.4. Animacja mrówek'),
  P('W trybie **A** każda iteracja jest rozłożona na wiele klatek animacji. Najpierw mrówki budują trasy (metoda construct_tours()), potem przez kilka sekund przechodzą po nich na planszy (rysowanych jest najwyżej 30 mrówek), a dopiero gdy wszystkie wrócą do mrowiska, feromon paruje i jest odkładany (update_pheromone()). Odpowiada to kolejności z pseudokodu i pokazuje, że feromon zmienia się raz na iterację. Suwak prędkości zmienia tempo ruchu mrówek, a przycisk „Krok” odtwarza jedną iterację i zatrzymuje animację.'),
  ...figure('gui_mrowki.png', 'Animacja mrówek: mrówki przechodzą swoje trasy w trakcie iteracji'),
  H2('6.5. Porównanie algorytmów'),
  ...figure('gui_porownanie.png', 'Tabela porównania algorytmów w panelu; na planszy pokazano trasę wyznaczoną algorytmem 2-opt. Czerwony znak X oznacza zablokowaną ścieżkę'),
];

const smallTable = table('Małe instancje: nadwyżka długości trasy względem optimum [%] i czas [ms] (średnia z 5 instancji)',
  ['n', 'ACO %', 'ACO ms', 'NN %', 'NN ms', '2-opt %', '2-opt ms', 'BF ms'],
  pivot(small, smallAlgos).map((r) => [r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[8]]),
  [700, 1196, 1196, 1196, 1196, 1196, 1196, 1196], { align: Array(8).fill(AlignmentType.RIGHT) });

const largeTable = table('Duże instancje: nadwyżka długości względem najlepszej znalezionej trasy [%] i czas [ms] (średnia z 3 instancji)',
  ['n', 'ACO %', 'ACO ms', 'NN %', 'NN ms', '2-opt %', '2-opt ms'],
  pivot(large, largeAlgos),
  [912, 1360, 1360, 1360, 1360, 1360, 1360], { align: Array(7).fill(AlignmentType.RIGHT) });

const convTable = table('Długość trasy po 150 iteracjach dla różnych parametrów (30 punktów, średnia z 3 uruchomień)',
  ['Wariant parametrów', 'Długość', 'Względem 2-opt'],
  conv.map(([w, l, g]) => [w, fmtNum(l, 1), (Number(g) > 0 ? '+' : '') + fmtNum(g, 1) + '%']),
  [4872, 2100, 2100], { align: [null, AlignmentType.RIGHT, AlignmentType.RIGHT] });

const s7 = [
  H1('7. Badania i wyniki wstępne'),
  H2('7.1. Metodyka'),
  bullet('Punkty (mrowisko i n punktów pożywienia) losowane są równomiernie w kwadracie 100 × 100; generator liczb losowych ma ustalone ziarno, dzięki czemu wyniki są powtarzalne.'),
  bullet('Algorytm mrówkowy: 20 mrówek, α = 1, β = 3, ρ = 0,3, 100 iteracji.'),
  bullet('Jakość trasy mierzona jest jako procentowa nadwyżka długości względem trasy optymalnej (małe instancje) lub najlepszej trasy znalezionej przez którąkolwiek z metod (duże instancje).'),
  bullet('Czas mierzony jest funkcją time.perf_counter() i obejmuje tylko obliczenia, bez rysowania.'),
  bullet('Wszystkie eksperymenty uruchamia skrypt **porownanie.py**; wyniki zapisuje do plików CSV i wykresów w katalogu wyniki/.'),
  P('Testy przeprowadzono na komputerze z systemem Windows 11 i Pythonem 3.13. Czasy bezwzględne zależą od sprzętu, ale proporcje między algorytmami powinny być podobne na innych komputerach.'),
  H2('7.2. Małe instancje – porównanie z optimum'),
  ...smallTable,
  ...figureFrom(RES, 'wykres_male.png', 'Małe instancje: nadwyżka długości względem optimum (po lewej) i czas obliczeń w skali logarytmicznej (po prawej)'),
  P(`Czas przeglądu zupełnego rośnie mniej więcej dziesięciokrotnie z każdym dodatkowym punktem: ${fmtMs(bf9[3])} ms dla 9 punktów i ${fmtMs(bf10[3])} ms dla 10 punktów. Przy tym tempie dla 15 punktów obliczenia trwałyby kilka dni. Algorytm mrówkowy potrzebuje od ${fmtNum(acoMs('3') / 1000)} do ${fmtNum(acoMs('10') / 1000)} s, a jego czas rośnie z liczbą punktów bardzo powoli, i znajduje trasy dłuższe od optymalnej średnio o mniej niż 1%. Algorytm 2-opt daje podobną jakość w ułamku milisekundy, a najbliższy sąsiad jest najszybszy, ale jego trasy są dłuższe od optymalnych nawet o kilkanaście procent.`),
  H2('7.3. Duże instancje'),
  ...largeTable,
  ...figureFrom(RES, 'wykres_duze.png', 'Duże instancje (10–100 punktów): jakość trasy i czas obliczeń'),
  P(`Dla większej liczby punktów różnica między najbliższym sąsiadem a pozostałymi metodami rośnie do około 15–24%. Algorytm mrówkowy i 2-opt dają trasy o podobnej jakości: w części instancji lepszy jest jeden, w części drugi, a różnice nie przekraczają kilku procent. Algorytm mrówkowy jest jednak znacznie wolniejszy (około ${fmtNum(acoMsLarge('100') / 1000, 1)} s dla 100 punktów przy 100 iteracjach), bo w każdej iteracji wiele mrówek buduje całe trasy.`),
  H2('7.4. Wpływ parametrów'),
  ...convTable,
  ...figureFrom(RES, 'wykres_zbieznosc.png', 'Długość najlepszej trasy w kolejnych iteracjach dla różnych ustawień parametrów'),
  P('Najważniejsza jest informacja o odległości: przy β = 0 mrówki wybierają kolejne punkty niemal losowo i po 150 iteracjach trasa jest dwukrotnie dłuższa niż przy ustawieniach domyślnych. Przy α = 0 feromon nie ma znaczenia, więc algorytm sprowadza się do losowej heurystyki zachłannej, która nie uczy się na wcześniejszych trasach; wynik jest o około 11% gorszy niż 2-opt. Współczynnik parowania ρ w badanym zakresie wpływał na wynik w niewielkim stopniu; przy szybkim parowaniu (ρ = 0,8) kolonia szybciej się ustala i kończy na nieco dłuższej trasie.'),
  H2('7.5. Rozszerzenie: zablokowanie ścieżki'),
  P('W aplikacji można w trakcie działania algorytmu zablokować dowolną ścieżkę (tryb „Blokowanie”). Kolonia zachowuje wtedy dotychczasowy feromon, a aplikacja wyświetla, po ilu iteracjach znaleziono trasę omijającą blokadę.'),
  ...figure('gui_blokada.png', 'Kolonia po zablokowaniu jednego z odcinków najlepszej trasy (czerwony znak X) znalazła trasę zastępczą'),
  P('W eksperymencie (20 punktów, 10 powtórzeń) kolonia przez 100 iteracji szukała trasy, potem blokowano losową krawędź najlepszej trasy. Mierzono, po ilu iteracjach kolonia znajduje trasę omijającą blokadę, a po ilu trasę dobrej jakości, czyli najwyżej o 3% dłuższą niż wynik 2-opt dla grafu z blokadą. Dla porównania ten sam cel mierzono dla kolonii uruchomionej od zera.'),
  ...figureFrom(RES, 'wykres_blokada.png', 'Średnia liczba iteracji potrzebnych po zablokowaniu ścieżki', { widthPx: 470 }),
  P(`Trasa omijająca blokadę pojawia się praktycznie od razu (średnio po ${blockVal(0)} iteracji), bo dotychczasowa najlepsza trasa staje się bardzo długa i każda trasa bez zablokowanej krawędzi ją zastępuje. Dojście do trasy dobrej jakości trwało jednak średnio ${blockVal(1)} iteracji przy zachowanym feromonie i tylko ${blockVal(2)} iteracji przy starcie od zera. Wynik ten pokazuje zjawisko stagnacji: po 100 iteracjach feromon jest silnie skupiony na starej trasie, więc mrówki z trudem odkrywają inne rozwiązania. W dalszej części projektu planujemy sprawdzić częściowe wyrównanie feromonu po zablokowaniu ścieżki oraz wariant MAX-MIN Ant System z górnym i dolnym ograniczeniem feromonu.`),
  H2('7.6. Wnioski wstępne'),
  bullet('Przegląd zupełny jest praktyczny tylko do około 10 punktów; służy jako punkt odniesienia dla pozostałych metod.'),
  bullet('Algorytm mrówkowy znajduje trasy bliskie optymalnym (dla małych instancji średnio poniżej 1% od optimum), a jego czas rośnie wielomianowo.'),
  bullet('Na losowych instancjach do 100 punktów podstawowy ACO daje wyniki porównywalne z 2-opt, ale jest od niego znacznie wolniejszy. Dobrym kierunkiem jest połączenie obu metod (ulepszanie tras mrówek algorytmem 2-opt).'),
  bullet('Kluczowe dla działania ACO jest uwzględnienie odległości (β > 0); feromon (α > 0) poprawia wynik względem samej heurystyki.'),
  bullet('Po zablokowaniu ścieżki kolonia od razu omija blokadę, ale skupiony feromon spowalnia dojście do nowej dobrej trasy.'),
];

const s8 = [
  H1('8. Plan dalszych prac'),
  ...table('Harmonogram prac',
    ['Etap', 'Zakres', 'Stan'],
    [
      ['Zajęcia 1', 'wybór tematu, wstępny opis projektu', 'zrobione'],
      ['Zajęcia 2', 'szczegółowy opis, klasyfikacja algorytmu i wyniki z literatury, dokumentacja, prezentacja; program z wizualizacją wzorów, podglądem prawdopodobieństw i animacją mrówek', 'zrobione (ten dokument)'],
      ['Do zajęć 3', 'ACO z ulepszaniem tras algorytmem 2-opt; wariant MAX-MIN Ant System; badanie częściowego resetu feromonu po blokadzie', 'planowane'],
      ['Do zajęć 3', 'więcej powtórzeń eksperymentów, odchylenie standardowe na wykresach, instancje z biblioteki TSPLIB (np. berlin52)', 'planowane'],
      ['Do zajęć 3', 'tryb krok po kroku z podziałem iteracji na etapy; zapis i wczytywanie planszy', 'planowane'],
      ['Zajęcia końcowe', 'ostateczna wersja programu, pełne wyniki, wnioski, prezentacja końcowa', 'planowane'],
    ], [1700, 5572, 1800]),
];

const s9 = [
  H1('Bibliografia'),
  ...[
    'M. Dorigo, T. Stützle, *Ant Colony Optimization*, MIT Press, Cambridge 2004.',
    'M. Dorigo, *Optimization, Learning and Natural Algorithms*, praca doktorska, Politecnico di Milano, 1992.',
    'B. Bullnheimer, R. F. Hartl, C. Strauss, *A new rank based version of the Ant System: a computational study*, Central European Journal for Operations Research and Economics, 7(1), 1999, s. 25–38.',
    'M. Dorigo, V. Maniezzo, A. Colorni, *Ant System: optimization by a colony of cooperating agents*, IEEE Transactions on Systems, Man, and Cybernetics – Part B, 26(1), 1996, s. 29–41.',
    'M. Dorigo, L. M. Gambardella, *Ant Colony System: a cooperative learning approach to the traveling salesman problem*, IEEE Transactions on Evolutionary Computation, 1(1), 1997, s. 53–66.',
    'T. Stützle, H. H. Hoos, *MAX–MIN Ant System*, Future Generation Computer Systems, 16(8), 2000, s. 889–914.',
    'S. Goss, S. Aron, J.-L. Deneubourg, J. M. Pasteels, *Self-organized shortcuts in the Argentine ant*, Naturwissenschaften, 76, 1989, s. 579–581.',
    'G. A. Croes, *A method for solving traveling-salesman problems*, Operations Research, 6(6), 1958, s. 791–812.',
    'D. L. Applegate, R. E. Bixby, V. Chvátal, W. J. Cook, *The Traveling Salesman Problem: A Computational Study*, Princeton University Press, 2006.',
    'Dokumentacja biblioteki Pygame, https://www.pygame.org/docs/',
  ].map((t) => numbered(t, 'biblio')),
];

const doc = new Document({
  creator: 'Projekt ACO-TSP',
  title: 'Zastosowanie algorytmu mrówkowego do problemu komiwojażera',
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 32, bold: true, font: FONT, color: '1F3864' }, paragraph: { spacing: { before: 240, after: 200 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 26, bold: true, font: FONT, color: '2F5496' }, paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1, keepNext: true } },
    ],
  },
  numbering: { config: [
    { reference: 'bullets', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    { reference: 'steps', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    { reference: 'biblio', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '[%1]', alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 720, hanging: 540 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1417, bottom: 1417, left: 1417, right: 1417 } },
      titlePage: true },
    footers: {
      default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
        children: [new TextRun({ children: [PageNumber.CURRENT], size: 18, color: '808080' })] })] }),
      first: new Footer({ children: [new Paragraph('')] }),
    },
    children: [...titlePage, ...s1, ...s2, ...s3, ...s4, ...s5, ...s6, ...s7, ...s8, ...s9],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  console.log('Zapisano', OUT, `(${figNo} rysunków, ${tabNo} tabel)`);
});
