# To Test with code

1. 'String', 'string_view' related funtions, e.g. sort, substr,find
2. 'map', 'unorder_map', 'set', etc
3. sort() algorithm with lamda function

    ``` cpp
    '
    auto comp = [](const widget& w1, const widget& w2)
    { return w1.weight() < w2.weight(); };

    sort(v.begin(), v.end(), comp);

    auto i = lower_bound(v.begin(), v.end(), widget{0}, comp);
    ```

4. 'try - catch - exception'