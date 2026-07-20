<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="ru">
<context>
    <name>ConnectedComponentsAlgorithm</name>
    <message>
        <source>Connected components (clusters)</source>
        <translation>Связные компоненты (кластеры)</translation>
    </message>
    <message>
        <source>Topology</source>
        <translation>Топология</translation>
    </message>
    <message>
        <source>Labels every line with the id of the independent sub-network (connected component) it belongs to. Lines connect where their &lt;b&gt;endpoints coincide&lt;/b&gt;.

Adds &lt;b&gt;cluster_id&lt;/b&gt; (ordered by size, 1 = largest network) and &lt;b&gt;cluster_size&lt;/b&gt; (edge count). A fully-connected network is a single component; extra components reveal gaps or stray features.

Run &lt;i&gt;Topology split&lt;/i&gt; first if the data has mid-segment crossings.</source>
        <translation>Присваивает каждой линии id независимой подсети (связной компоненты), к которой она относится. Линии считаются связанными там, где &lt;b&gt;совпадают их концы&lt;/b&gt;.

Добавляет &lt;b&gt;cluster_id&lt;/b&gt; (по убыванию размера, 1 = крупнейшая сеть) и &lt;b&gt;cluster_size&lt;/b&gt; (число рёбер). Полностью связная сеть — одна компонента; лишние компоненты указывают на разрывы или отдельные объекты.

Если в данных есть пересечения в середине сегментов, сначала выполните &lt;i&gt;Топологическое разбиение&lt;/i&gt;.</translation>
    </message>
    <message>
        <source>Input line layer</source>
        <translation>Входной слой линий</translation>
    </message>
    <message>
        <source>Lines with cluster id</source>
        <translation>Линии с id кластера</translation>
    </message>
    <message>
        <source>No usable line geometries in the input.</source>
        <translation>Во входных данных нет пригодных линейных геометрий.</translation>
    </message>
    <message>
        <source>Done: {n} components from {edges} edges (largest = cluster 1).</source>
        <translation>Готово: {n} компонент из {edges} рёбер (крупнейшая = кластер 1).</translation>
    </message>
</context>
<context>
    <name>DangleResolverAlgorithm</name>
    <message>
        <source>Resolve dangles (extend / trim)</source>
        <translation>Разрешение висячих концов (достройка / обрезка)</translation>
    </message>
    <message>
        <source>Topology</source>
        <translation>Топология</translation>
    </message>
    <message>
        <source>Cleans dangling ends of a line network, keeping one output feature per input feature (attributes preserved).

&lt;b&gt;Undershoot → extend:&lt;/b&gt; a free end that stops short of another line is extended &lt;i&gt;along its own direction&lt;/i&gt; until it reaches that line, if the gap is within the &lt;b&gt;Tolerance&lt;/b&gt;.

&lt;b&gt;Overshoot → trim:&lt;/b&gt; a free end that runs past a crossing, leaving a tail shorter than the &lt;b&gt;Tolerance&lt;/b&gt;, is cut back to that crossing.

Tolerance is in the layer's map units. This tool does not split lines — run &lt;i&gt;Topology split&lt;/i&gt; afterwards to node the network.</source>
        <translation>Чистит висячие концы линейной сети, сохраняя по одному объекту на входной объект (атрибуты сохраняются).

&lt;b&gt;Недотяг → достройка:&lt;/b&gt; свободный конец, не дошедший до другой линии, продлевается &lt;i&gt;вдоль своего направления&lt;/i&gt; до этой линии, если зазор в пределах &lt;b&gt;Допуска&lt;/b&gt;.

&lt;b&gt;Перехлёст → обрезка:&lt;/b&gt; свободный конец, проскочивший за пересечение и оставивший хвост короче &lt;b&gt;Допуска&lt;/b&gt;, обрезается до этого пересечения.

Допуск — в единицах карты слоя. Инструмент не разбивает линии — для нодирования сети выполните затем &lt;i&gt;Топологическое разбиение&lt;/i&gt;.</translation>
    </message>
    <message>
        <source>Input line layer</source>
        <translation>Входной слой линий</translation>
    </message>
    <message>
        <source>Tolerance (max gap to close / tail to trim)</source>
        <translation>Допуск (макс. зазор для достройки / хвост для обрезки)</translation>
    </message>
    <message>
        <source>Extend undershoots</source>
        <translation>Достраивать недотяги</translation>
    </message>
    <message>
        <source>Trim overshoots</source>
        <translation>Обрезать перехлёсты</translation>
    </message>
    <message>
        <source>Resolved lines</source>
        <translation>Обработанные линии</translation>
    </message>
    <message>
        <source>No usable line geometries in the input.</source>
        <translation>Во входных данных нет пригодных линейных геометрий.</translation>
    </message>
    <message>
        <source>Done: {ext} ends extended, {trim} ends trimmed.</source>
        <translation>Готово: достроено концов — {ext}, обрезано — {trim}.</translation>
    </message>
</context>
<context>
    <name>PseudoNodeCollapseAlgorithm</name>
    <message>
        <source>Collapse pseudo-nodes</source>
        <translation>Схлопывание псевдоузлов</translation>
    </message>
    <message>
        <source>Topology</source>
        <translation>Топология</translation>
    </message>
    <message>
        <source>Merges chains of lines that meet only at &lt;b&gt;degree-2 nodes&lt;/b&gt; (pseudo-nodes) into single lines running junction-to-junction.

• Lines are joined only where their &lt;b&gt;endpoints coincide&lt;/b&gt;. If your data has mid-segment crossings, run &lt;i&gt;Topology split&lt;/i&gt; first.
• Nodes where 3+ lines meet, and dead-ends, are kept.
• &lt;b&gt;Group field&lt;/b&gt; (optional): only merge across a node when both lines share the same value of this field.

Output is single-part LineStrings; a merged line inherits the attributes of its longest input segment.</source>
        <translation>Объединяет цепочки линий, сходящиеся только в &lt;b&gt;узлах степени 2&lt;/b&gt; (псевдоузлах), в единые линии от перекрёстка до перекрёстка.

• Линии соединяются только там, где &lt;b&gt;совпадают их концы&lt;/b&gt;. Если в данных есть пересечения в середине сегментов, сначала выполните &lt;i&gt;Топологическое разбиение&lt;/i&gt;.
• Узлы, где сходятся 3+ линии, и тупики сохраняются.
• &lt;b&gt;Поле группировки&lt;/b&gt; (необязательно): сливать через узел только если у обеих линий одинаковое значение этого поля.

Выход — одночастные линии; объединённая линия наследует атрибуты самого длинного исходного сегмента.</translation>
    </message>
    <message>
        <source>Input line layer</source>
        <translation>Входной слой линий</translation>
    </message>
    <message>
        <source>Group field (only merge where equal)</source>
        <translation>Поле группировки (сливать только при равенстве)</translation>
    </message>
    <message>
        <source>Merged lines</source>
        <translation>Объединённые линии</translation>
    </message>
    <message>
        <source>No usable line geometries in the input.</source>
        <translation>Во входных данных нет пригодных линейных геометрий.</translation>
    </message>
    <message>
        <source>Done: {out} merged lines from {edges} input segments.</source>
        <translation>Готово: {out} объединённых линий из {edges} исходных сегментов.</translation>
    </message>
</context>
<context>
    <name>TopologySplitAlgorithm</name>
    <message>
        <source>Topology split</source>
        <translation>Топологическое разбиение</translation>
    </message>
    <message>
        <source>Topology</source>
        <translation>Топология</translation>
    </message>
    <message>
        <source>Rebuilds line topology on a single line layer.

• Splits both lines at every crossing (X) and where one line's end touches another line (T).
• Optionally extends a dangling line end, along its own direction, up to the &lt;b&gt;Snap/extend tolerance&lt;/b&gt;, until it meets another line — then splits there too.
• Output features are single-part LineStrings running node-to-node; the shape between nodes and all attributes are preserved.

&lt;b&gt;Snap/extend tolerance&lt;/b&gt; is in the layer's map units. Set it to 0 to disable extension and only node existing intersections.</source>
        <translation>Перестраивает топологию одного слоя линий.

• Разбивает обе линии в каждом пересечении (X) и там, где конец одной линии касается другой (T).
• По желанию продлевает висячий конец линии вдоль его направления в пределах &lt;b&gt;Допуска привязки/достройки&lt;/b&gt;, пока он не встретит другую линию — и разбивает и там.
• Выходные объекты — одночастные линии от узла до узла; форма между узлами и все атрибуты сохраняются.

&lt;b&gt;Допуск привязки/достройки&lt;/b&gt; — в единицах карты слоя. Установите 0, чтобы отключить достройку и только нодировать существующие пересечения.</translation>
    </message>
    <message>
        <source>Input line layer</source>
        <translation>Входной слой линий</translation>
    </message>
    <message>
        <source>Snap/extend tolerance (0 = no extension)</source>
        <translation>Допуск привязки/достройки (0 = без достройки)</translation>
    </message>
    <message>
        <source>Noded lines</source>
        <translation>Нодированные линии</translation>
    </message>
    <message>
        <source>No usable line geometries in the input.</source>
        <translation>Во входных данных нет пригодных линейных геометрий.</translation>
    </message>
    <message>
        <source>Extending dangling ends…</source>
        <translation>Достройка висячих концов…</translation>
    </message>
    <message>
        <source>Computing intersections…</source>
        <translation>Вычисление пересечений…</translation>
    </message>
    <message>
        <source>Splitting lines at nodes…</source>
        <translation>Разбиение линий в узлах…</translation>
    </message>
    <message>
        <source>Done: {parts} parts from {inputs} lines, {ext} ends extended.</source>
        <translation>Готово: {parts} частей из {inputs} линий, достроено концов — {ext}.</translation>
    </message>
</context>
</TS>
