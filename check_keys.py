import os
for name in ["FMP_API_KEY", "ORATS_API_KEY", "UW_API_KEY", "UNUSUAL_WHALES_API_TOKEN"]:
    v = os.environ.get(name)
    print(f"{name:28} {'set (' + v[:4] + '…' + v[-3:] + ')' if v else 'MISSING'}")