# === PANDAS .all() FONKSİYONU ===

import pandas as pd
import numpy as np

print("="*60)
print("PANDAS .all() FONKSİYONU NEDİR?")
print("="*60)

# Örnek veriler
data1 = [True, True, True, True, True]
data2 = [True, True, False, True, True]  
data3 = [False, False, False, False, False]
data4 = [True, True, True, True, True]

series1 = pd.Series(data1)
series2 = pd.Series(data2)
series3 = pd.Series(data3)
series4 = pd.Series(data4)

print("Örnek veriler:")
print(f"series1: {data1}")
print(f"series2: {data2}")
print(f"series3: {data3}")
print(f"series4: {data4}")

print("\n.all() sonuçları:")
print(f"series1.all(): {series1.all()}")  # True - hepsi True
print(f"series2.all(): {series2.all()}")  # False - bir tane False var
print(f"series3.all(): {series3.all()}")  # False - hepsi False
print(f"series4.all(): {series4.all()}")  # True - hepsi True

print("\n" + "="*60)
print(".all() MANTIGI")
print("="*60)

print("""
.all() fonksiyonu:
✅ Tüm değerler True ise -> True döner
❌ En az bir değer False ise -> False döner

Mantık:
- True and True and True and True -> True
- True and True and False and True -> False
""")

# === MANUAL KARŞILAŞTIRMA ===
print("\n" + "="*60)
print("MANUAL KARŞILAŞTIRMA")
print("="*60)

def manual_all_check(series):
    """Manual olarak .all() fonksiyonunu taklit et"""
    for value in series:
        if not value:  # Eğer False ise
            return False
    return True

print("Manual vs .all() karşılaştırması:")
test_series = pd.Series([True, True, False, True])
print(f"Series: {test_series.tolist()}")
print(f"Manual check: {manual_all_check(test_series)}")
print(f"Pandas .all(): {test_series.all()}")

# === FARKLI VERI TİPLERİYLE ===
print("\n" + "="*60)
print("FARKLI VERI TİPLERİYLE")
print("="*60)

# Sayısal değerler
numbers = pd.Series([1, 2, 3, 4, 5])
print(f"Sayılar: {numbers.tolist()}")
print(f"numbers.all(): {numbers.all()}")  # True - hiçbi