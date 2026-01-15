import pandas as pd
try:
    s = pd.Series({('listing', 'symbol'): 'HNX30'})
    print("Series created:", s)
    
    val1 = s.get(('match', 'match_price'))
    print("Val1:", val1)
    
    val2 = s.get(('trading', 'total_value'))
    print("Val2:", val2)
    
    print("Success")
except Exception as e:
    print("Error:", e)
