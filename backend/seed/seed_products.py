import asyncio
import sys
from sqlalchemy import select, delete
from backend.database.connection import async_session, init_db
from backend.database.models import ProductModel


def L(pid, name, brand, price, stock, cpu, gpu, ram, storage, hz):
    return dict(id=pid, name=name, brand=brand, category="laptop", price=price, stock=stock,
                cpu=cpu, gpu=gpu, ram_gb=ram, storage=storage, refresh_rate_hz=hz,
                spec_summary=f"{cpu} {gpu} {ram}GB {storage} {hz}Hz",
                return_days=7, warranty_years=1, delivery_days=2)


def P(pid, name, brand, cat, price, stock, summary, warranty=1, delivery=2, hz=None, ram=None):
    return dict(id=pid, name=name, brand=brand, category=cat, price=price, stock=stock,
                cpu=None, gpu=None, ram_gb=ram, storage=None, refresh_rate_hz=hz,
                spec_summary=summary, return_days=7, warranty_years=warranty, delivery_days=delivery)


LAPTOPS = [
    L("LAP001","Acer Aspire 7","Acer",42990,12,"i5-12450H","GTX 1650",8,"512GB SSD",60),
    L("LAP002","Lenovo IdeaPad Gaming 3","Lenovo",47990,9,"Ryzen 5 5600H","GTX 1650",8,"512GB SSD",120),
    L("LAP003","HP Victus 15","HP",52990,15,"i5-12500H","RTX 3050",8,"512GB SSD",144),
    L("LAP004","ASUS TUF Gaming F15","ASUS",54990,7,"i5-12450H","RTX 3050",16,"512GB SSD",144),
    L("LAP005","Dell G15","Dell",49990,11,"i5-12500H","RTX 2050",8,"512GB SSD",120),
    L("LAP006","ASUS TUF Gaming A15","ASUS",62990,8,"Ryzen 7 7435HS","RTX 4050",16,"1TB SSD",144),
    L("LAP007","HP Victus 16","HP",64990,10,"i7-13620H","RTX 4050",16,"512GB SSD",144),
    L("LAP008","Lenovo LOQ 15","Lenovo",66990,6,"i7-13650HX","RTX 4050",16,"512GB SSD",144),
    L("LAP009","Acer Nitro 5","Acer",59990,13,"i5-13420H","RTX 4050",16,"512GB SSD",144),
    L("LAP010","ASUS ROG Strix G15","ASUS",71990,5,"Ryzen 7 7735HS","RTX 4060",16,"1TB SSD",144),
    L("LAP011","MSI Cyborg 15","MSI",68990,9,"i7-13620H","RTX 4050",16,"1TB SSD",144),
    L("LAP012","Dell G16","Dell",69990,7,"i7-13650HX","RTX 4050",16,"1TB SSD",165),
    L("LAP013","HP Omen 16","HP",74990,4,"i7-13700H","RTX 4060",16,"1TB SSD",144),
    L("LAP014","Lenovo LOQ 15 Ryzen","Lenovo",58990,14,"Ryzen 5 7535HS","RTX 4050",16,"512GB SSD",144),
    L("LAP015","ASUS TUF Gaming A16","ASUS",73990,6,"Ryzen 7 7435HS","RTX 4060",16,"1TB SSD",165),
    L("LAP016","ASUS ROG Strix G16","ASUS",84990,5,"i7-13650HX","RTX 4060",16,"1TB SSD",165),
    L("LAP017","MSI Katana 15","MSI",79990,8,"i7-13620H","RTX 4060",16,"1TB SSD",144),
    L("LAP018","Lenovo Legion 5 Pro","Lenovo",94990,4,"Ryzen 7 7745HX","RTX 4060",16,"1TB SSD",165),
    L("LAP019","HP Omen 17","HP",99990,3,"i9-13900H","RTX 4070",32,"1TB SSD",165),
    L("LAP020","ASUS ROG Zephyrus G14","ASUS",109990,3,"Ryzen 9 8945HS","RTX 4060",32,"1TB SSD",165),
    L("LAP021","Dell G16 i9","Dell",89990,6,"i9-13900HX","RTX 4060",16,"1TB SSD",165),
    L("LAP022","Lenovo Legion Pro 5i","Lenovo",114990,2,"i9-13900HX","RTX 4070",32,"1TB SSD",165),
    L("LAP023","ASUS ROG Strix G18","ASUS",119990,2,"i9-13980HX","RTX 4070",32,"1TB SSD",165),
    L("LAP024","Dell XPS 13","Dell",89990,6,"i7-1355U","Intel Iris Xe",16,"512GB SSD",60),
    L("LAP025","ASUS Zenbook 14","ASUS",64990,10,"Ryzen 7 7730U","AMD Radeon",16,"512GB SSD",60),
    L("LAP026","Lenovo ThinkPad E14","Lenovo",54990,12,"i5-1335U","Intel Iris Xe",8,"512GB SSD",60),
    L("LAP027","HP Pavilion 14","HP",49990,14,"i5-1235U","Intel Iris Xe",8,"512GB SSD",60),
    L("LAP028","Acer Swift 3","Acer",46990,11,"Ryzen 5 5500U","AMD Radeon",8,"512GB SSD",60),
    L("LAP029","MacBook Air M2","Apple",99900,5,"Apple M2","Apple GPU 8-core",8,"256GB SSD",60),
    L("LAP030","ASUS Vivobook Pro 15","ASUS",61990,9,"i5-13500H","RTX 3050",16,"512GB SSD",60),
    L("LAP031","Lenovo IdeaPad Slim 3","Lenovo",38990,18,"Ryzen 3 7320U","AMD Radeon",8,"256GB SSD",60),
    L("LAP032","HP 15s","HP",36990,20,"i3-1215U","Intel UHD",8,"512GB SSD",60),
    L("LAP033","Acer Aspire Lite","Acer",33990,16,"Ryzen 5 5500U","AMD Radeon",8,"512GB SSD",60),
    L("LAP034","MacBook Air M3","Apple",114900,4,"Apple M3","Apple GPU 10-core",16,"512GB SSD",60),
    L("LAP035","MSI Thin 15","MSI",56990,10,"i5-12450H","RTX 3050",16,"512GB SSD",144),
]

MONITORS = [
    P("MON001","Acer Nitro 24-inch 165Hz","Acer","monitor",11990,14,"24 inch 1080p IPS 165Hz 1ms gaming",3,3,165),
    P("MON002","LG UltraGear 27-inch 144Hz","LG","monitor",18990,9,"27 inch 1440p IPS 144Hz 1ms gaming",3,3,144),
    P("MON003","Samsung Odyssey G5 27-inch","Samsung","monitor",21990,7,"27 inch 1440p VA 165Hz curved gaming",3,3,165),
    P("MON004","Dell S2422HZ 24-inch","Dell","monitor",14990,11,"24 inch 1080p IPS 75Hz webcam video calls",3,3,75),
    P("MON005","BenQ GW2485 24-inch","BenQ","monitor",9990,16,"24 inch 1080p IPS 75Hz eye care office",3,3,75),
    P("MON006","LG 32-inch 4K UHD","LG","monitor",32990,5,"32 inch 4K UHD IPS 60Hz colour accurate",3,3,60),
    P("MON007","ASUS TUF VG249Q1A","ASUS","monitor",13490,12,"24 inch 1080p IPS 165Hz 1ms gaming",3,3,165),
    P("MON008","Samsung 22-inch Essential","Samsung","monitor",7490,20,"22 inch 1080p IPS 75Hz budget office",3,3,75),
    P("MON009","Dell UltraSharp U2723QE","Dell","monitor",44990,3,"27 inch 4K IPS Black 60Hz USB-C professional",3,4,60),
    P("MON010","MSI G274F 27-inch","MSI","monitor",16990,8,"27 inch 1080p IPS 180Hz 1ms gaming",3,3,180),
    P("MON011","LG 34-inch UltraWide","LG","monitor",38990,4,"34 inch ultrawide 1440p IPS 100Hz productivity",3,4,100),
    P("MON012","ViewSonic VA2432 24-inch","ViewSonic","monitor",8990,18,"24 inch 1080p IPS 75Hz office budget",3,3,75),
]

GPUS = [
    P("GPU001","NVIDIA RTX 4060 8GB","NVIDIA","gpu",29990,8,"RTX 4060 8GB GDDR6 1080p gaming",3,3),
    P("GPU002","NVIDIA RTX 4060 Ti 8GB","NVIDIA","gpu",39990,6,"RTX 4060 Ti 8GB GDDR6 1440p gaming",3,3),
    P("GPU003","NVIDIA RTX 4070 12GB","NVIDIA","gpu",54990,5,"RTX 4070 12GB GDDR6X 1440p high refresh",3,3),
    P("GPU004","NVIDIA RTX 4070 Super","NVIDIA","gpu",64990,4,"RTX 4070 Super 12GB GDDR6X 1440p 4K",3,3),
    P("GPU005","NVIDIA RTX 4080 Super 16GB","NVIDIA","gpu",109990,2,"RTX 4080 Super 16GB GDDR6X 4K gaming",3,3),
    P("GPU006","AMD Radeon RX 7600 8GB","AMD","gpu",24990,10,"RX 7600 8GB GDDR6 1080p gaming",3,3),
    P("GPU007","AMD Radeon RX 7700 XT","AMD","gpu",44990,6,"RX 7700 XT 12GB GDDR6 1440p gaming",3,3),
    P("GPU008","AMD Radeon RX 7800 XT","AMD","gpu",54990,4,"RX 7800 XT 16GB GDDR6 1440p 4K",3,3),
    P("GPU009","NVIDIA RTX 3050 8GB","NVIDIA","gpu",19990,12,"RTX 3050 8GB GDDR6 entry gaming",3,3),
    P("GPU010","NVIDIA GTX 1650 4GB","NVIDIA","gpu",12990,15,"GTX 1650 4GB GDDR6 budget gaming",3,3),
]

PROCESSORS = [
    P("CPU001","Intel Core i5-13400F","Intel","processor",17990,12,"i5 13400F 10 core 4.6GHz LGA1700 gaming",3,3),
    P("CPU002","Intel Core i5-14600K","Intel","processor",26990,8,"i5 14600K 14 core 5.3GHz LGA1700 unlocked",3,3),
    P("CPU003","Intel Core i7-14700K","Intel","processor",39990,6,"i7 14700K 20 core 5.6GHz LGA1700 unlocked",3,3),
    P("CPU004","Intel Core i9-14900K","Intel","processor",56990,3,"i9 14900K 24 core 6.0GHz LGA1700 flagship",3,3),
    P("CPU005","AMD Ryzen 5 7600","AMD","processor",19990,14,"Ryzen 5 7600 6 core 5.1GHz AM5 gaming",3,3),
    P("CPU006","AMD Ryzen 5 7600X","AMD","processor",22990,10,"Ryzen 5 7600X 6 core 5.3GHz AM5 gaming",3,3),
    P("CPU007","AMD Ryzen 7 7800X3D","AMD","processor",38990,5,"Ryzen 7 7800X3D 8 core 3D V-Cache AM5 gaming",3,3),
    P("CPU008","AMD Ryzen 9 7900X","AMD","processor",42990,4,"Ryzen 9 7900X 12 core 5.6GHz AM5 workstation",3,3),
    P("CPU009","Intel Core i3-13100F","Intel","processor",10990,16,"i3 13100F 4 core 4.5GHz LGA1700 budget",3,3),
    P("CPU010","AMD Ryzen 5 5600","AMD","processor",12990,18,"Ryzen 5 5600 6 core 4.4GHz AM4 budget",3,3),
]

MICE = [
    P("MOU001","Logitech M221 Silent","Logitech","mouse",799,60,"wireless silent click 1000 DPI compact",1,2),
    P("MOU002","HP 250 Wireless","HP","mouse",649,80,"wireless 1600 DPI ambidextrous office",1,2),
    P("MOU003","Redgear A-15 Gaming","Redgear","mouse",1199,40,"wired RGB 12400 DPI gaming 7 buttons",1,2),
    P("MOU004","Logitech G102 Lightsync","Logitech","mouse",1795,35,"wired RGB 8000 DPI gaming lightweight",2,2),
    P("MOU005","Razer DeathAdder V2 X","Razer","mouse",3490,18,"wireless 14000 DPI gaming ergonomic",2,2),
    P("MOU006","Logitech MX Master 3S","Logitech","mouse",8995,10,"wireless 8000 DPI productivity silent MagSpeed",2,2),
    P("MOU007","Zebronics Zeb-Transformer","Zebronics","mouse",549,70,"wired RGB 3200 DPI budget gaming",1,2),
    P("MOU008","Logitech G304 Lightspeed","Logitech","mouse",2995,22,"wireless 12000 DPI gaming HERO sensor",2,2),
    P("MOU009","Dell MS116 Optical","Dell","mouse",449,90,"wired 1000 DPI plug and play office",1,2),
    P("MOU010","Razer Basilisk V3","Razer","mouse",5490,12,"wired RGB 26000 DPI gaming 11 buttons",2,2),
]

MOUSEPADS = [
    P("PAD001","Redgear MP35 Speed","Redgear","mousepad",299,80,"medium 350x250mm stitched edge speed cloth",1,2),
    P("PAD002","Logitech G240 Cloth","Logitech","mousepad",1195,30,"medium cloth low friction gaming",1,2),
    P("PAD003","Cosmic Byte Equinox XL","Cosmic Byte","mousepad",799,45,"extended XL 800x300mm RGB desk mat",1,2),
    P("PAD004","Zebronics Zeb-XL","Zebronics","mousepad",449,60,"extended 700x300mm anti-slip base",1,2),
    P("PAD005","Razer Goliathus Extended","Razer","mousepad",2490,15,"extended chroma RGB 920x294mm gaming",1,2),
    P("PAD006","HP MP3524 Gaming","HP","mousepad",349,70,"medium 350x240mm rubber base",1,2),
    P("PAD007","Corsair MM300 Medium","Corsair","mousepad",1690,20,"medium 360x300mm anti-fray stitched",1,2),
    P("PAD008","Amkette Basic Pad","Amkette","mousepad",149,100,"small 220x180mm budget office",1,2),
]

STANDS = [
    P("STD001","Portronics My Buddy K3","Portronics","laptop_stand",1299,40,"aluminium adjustable 6 angle foldable 15.6 inch",1,2),
    P("STD002","Zinq Aluminium Riser","Zinq","laptop_stand",899,50,"aluminium fixed riser ventilated 15.6 inch",1,2),
    P("STD003","Rise Ergonomic Pro","Rise","laptop_stand",1899,25,"aluminium height adjustable ergonomic 17 inch",1,2),
    P("STD004","Amkette Foldable Stand","Amkette","laptop_stand",699,60,"plastic foldable portable travel lightweight",1,2),
    P("STD005","Portronics Modesk Deluxe","Portronics","laptop_stand",2499,15,"aluminium sit stand desk converter adjustable",1,3),
    P("STD006","Callas Ventilated Stand","Callas","laptop_stand",1099,35,"aluminium ventilated cooling 6 level 15.6 inch",1,2),
    P("STD007","Boya Vertical Dock Stand","Boya","laptop_stand",1499,20,"vertical dock space saving desk 17 inch",1,2),
    P("STD008","Green Soul Basic Riser","Green Soul","laptop_stand",549,55,"plastic foldable budget riser 14 inch",1,2),
]

SPEAKERS = [
    P("SPK001","boAt Aavante Bar 1200","boAt","speakers",3499,25,"soundbar 60W bluetooth RGB desktop",1,2),
    P("SPK002","Zebronics Zeb-Bt6790RUCF","Zebronics","speakers",2299,30,"2.1 channel 40W subwoofer bluetooth",1,2),
    P("SPK003","Logitech Z313 2.1","Logitech","speakers",4295,18,"2.1 channel 25W subwoofer wired desktop",2,2),
    P("SPK004","Creative Pebble V3","Creative","speakers",3990,20,"2.0 channel 8W USB-C bluetooth compact",1,2),
    P("SPK005","JBL Quantum Duo","JBL","speakers",8999,8,"2.0 channel RGB gaming bluetooth 3D surround",1,3),
    P("SPK006","boAt Stone 350","boAt","speakers",1799,40,"portable bluetooth 10W IPX7 waterproof",1,2),
    P("SPK007","Logitech Z407","Logitech","speakers",8495,9,"2.1 channel 80W bluetooth wireless control",2,3),
    P("SPK008","Zebronics Zeb-County","Zebronics","speakers",799,60,"portable bluetooth 3W FM radio budget",1,2),
    P("SPK009","Sony SRS-XB13","Sony","speakers",3490,22,"portable bluetooth extra bass IPX67 compact",1,2),
    P("SPK010","Edifier R1280T Bookshelf","Edifier","speakers",8999,7,"2.0 bookshelf 42W wooden studio monitor",2,3),
]

KEYBOARDS = [
    P("KEY001","Logitech K120 Wired","Logitech","keyboard",599,45,"wired membrane full size spill resistant office",1,2),
    P("KEY002","Redgear Shadow Blade","Redgear","keyboard",2499,18,"wired mechanical blue switch RGB gaming",2,2),
    P("KEY003","Logitech MX Keys Mini","Logitech","keyboard",9495,8,"wireless backlit compact productivity bluetooth",2,2),
    P("KEY004","Zebronics Max Plus","Zebronics","keyboard",1799,25,"wired mechanical RGB brown switch gaming",1,2),
    P("KEY005","HP K500F Membrane","HP","keyboard",1099,30,"wired membrane RGB metal body gaming",1,2),
    P("KEY006","Razer Cynosa V2","Razer","keyboard",4990,10,"wired membrane chroma RGB gaming",2,2),
    P("KEY007","Dell KB216 Multimedia","Dell","keyboard",749,50,"wired membrane full size multimedia office",1,2),
    P("KEY008","Keychron K2 Wireless","Keychron","keyboard",7499,6,"wireless mechanical hot swappable 75 percent",2,3),
]

OTHERS = [
    P("ACC011","boAt Rockerz 450 Headphones","boAt","headphones",1799,40,"wireless over ear 40mm bluetooth 15 hours",1,2),
    P("ACC012","JBL Tune 510BT","JBL","headphones",3499,20,"wireless on ear bluetooth 40 hours pure bass",1,2),
    P("ACC013","HyperX Cloud Stinger 2","HyperX","headphones",4990,12,"wired gaming headset 50mm mic noise cancel",2,2),
    P("ACC004","American Tourister Laptop Backpack","American Tourister","bag",1499,35,"backpack 15.6 inch padded water resistant",1,2),
    P("ACC005","HP Laptop Sleeve 15.6","HP","bag",899,50,"sleeve 15.6 inch padded slim",1,2),
    P("ACC006","Targus Classic Backpack","Targus","bag",2199,20,"backpack 15.6 inch multi compartment",1,2),
    P("ACC007","Cosmic Byte Cooling Pad","Cosmic Byte","cooling_pad",1299,25,"5 fan RGB adjustable height 17 inch",1,2),
    P("ACC008","Havit F2056 Cooling Pad","Havit","cooling_pad",999,30,"3 fan slim portable 15.6 inch",1,2),
    P("ACC013W","1-Year Extended Warranty","Elventa","warranty",2999,999,"extended coverage 1 year parts labour",0,1),
    P("ACC014W","2-Year Extended Warranty","Elventa","warranty",4999,999,"extended coverage 2 years parts labour",0,1),
    P("ACC015W","Accidental Damage Protection","Elventa","warranty",3499,999,"accidental damage liquid spill drop cover",0,1),
]

ALL = LAPTOPS + MONITORS + GPUS + PROCESSORS + MICE + MOUSEPADS + STANDS + SPEAKERS + KEYBOARDS + OTHERS


async def seed():
    await init_db()
    async with async_session() as session:
        existing = await session.execute(select(ProductModel))
        count = len(existing.scalars().all())

        if count > 0 and "--reset" not in sys.argv:
            print(f"Database already has {count} products. Run with --reset to wipe and reseed.")
            return

        if "--reset" in sys.argv:
            await session.execute(delete(ProductModel))
            await session.commit()
            print("Cleared existing products.")

        for p in ALL:
            session.add(ProductModel(**p))
        await session.commit()

        by_cat = {}
        for p in ALL:
            by_cat[p["category"]] = by_cat.get(p["category"], 0) + 1
        print(f"Seeded {len(ALL)} products:")
        for cat, n in sorted(by_cat.items()):
            print(f"  {cat}: {n}")


if __name__ == "__main__":
    asyncio.run(seed())