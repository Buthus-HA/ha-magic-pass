"""Sample payloads (trimmed copies of the real pages)."""

def row(slug, name, state, lifts, km, info=""):
    css = "bg-success" if state != "Fermé" else "bg-danger"
    marker = "open" if state != "Fermé" else "close"
    info_html = (
        f'<span class="text-gray-500 text-sm lg:text-base font-medium mt-6 lg:mt-6 block"> {info} </span>' if info else ""
    )
    return f'''<a href="/fr/stations/{slug}" class="group grid" aria-label="{name}"> <span class="grow lg:col-span-2">
 <span class="md:flex"> <span class="block"> {name} </span> <span class="inline-flex">
 <div class="opening-state {css} inline-block"> {state} </div>
 <span class="marker-icon marker-icon--sm marker-icon--{marker} " title="{state}" aria-hidden="true"></span> </span> </span>
 {info_html} </span>
 <span class="grow"><span><span class="block"> <small class="md:hidden">Installations ouvertes</small> <span class="text-danger">{lifts}</span> </span></span></span>
 <span class="grow"><span><span class="block"> <small class="md:hidden">Pistes ouvertes</small> <span class="text-danger">{km} <small>km</small></span> </span></span></span>
 </a>'''


FILTERS = '''<div><input name="states[]" v-model="filters.states"
 type="checkbox" :value="10"
 class="form-checkbox" id="filter-10">
 </div>
 <label class="font-medium text-xs ml-16 grow" for="filter-10">
 Fribourg
 </label>
 <div><input name="states[]" v-model="filters.states" type="checkbox" :value="8" class="form-checkbox" id="filter-8"></div>
 <label class="font-medium" for="filter-8"> Vaud </label>'''


def opening_page(charmey_state="Fermé", charmey_lifts="0/7", charmey_km="0/29.2"):
    rows = (
        row("charmey-14", "Charmey", charmey_state, charmey_lifts, charmey_km,
            "<p><strong><u>Ouverture :</u></strong></p><p>19.12.2026 - 07.03.2027</p><p>Week-ends + 05.12 - 13.12.2026</p>")
        + row("villars-gryon-37", "Villars-Gryon", "Ouvert", "2/21", "10/65")
        + row("les-rochers--de--naye-90", "Les Rochers - de - Naye", "Fermé", "0/3", "0/5")
    )
    return f"<html><body><bd-resorts-opening inline-template><div>{FILTERS}{rows}</div></bd-resorts-opening></body></html>"


def region_page(region):
    if region == "10":
        return f"<bd-resorts-opening>{row('charmey-14', 'Charmey', 'Fermé', '0/7', '0/29.2')}</bd-resorts-opening>"
    return (
        "<bd-resorts-opening>"
        + row("villars-gryon-37", "Villars-Gryon", "Ouvert", "2/21", "10/65")
        + row("les-rochers--de--naye-90", "Les Rochers - de - Naye", "Fermé", "0/3", "0/5")
        + "</bd-resorts-opening>"
    )


MARKERS = [
    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [7.1678, 46.6189]}, "properties": {"family": "destinations", "objectId": "destinations/charmey"}},
    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [7.0528, 46.3019]}, "properties": {"family": "destinations", "objectId": "destinations/villars-gryon"}},
    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [6.9734, 46.4318]}, "properties": {"family": "destinations", "objectId": "destinations/les-rochers-de-naye"}},
    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [7.17, 46.62]}, "properties": {"family": "ski_trail", "category": "ski_easy"}},
    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [7.171, 46.621]}, "properties": {"family": "ski_trail", "category": "ski_advanced"}},
    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [7.05, 46.30]}, "properties": {"family": "ski_trail", "category": "ski_novice"}},
    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [7.0, 46.0]}, "properties": {"family": "restaurants", "category": "restaurant"}},
]

OSRM = {"code": "Ok", "durations": [[0, 1020, 3240, 2700]]}


def meteo(n):
    hours = [f"2026-11-{d:02d}T{h:02d}:00" for d in range(20, 25) for h in range(24)]
    one = {
        "hourly": {"time": hours, "snowfall": [0.5] * len(hours)},
        "daily": {
            "time": ["2026-11-20", "2026-11-21", "2026-11-22", "2026-11-23", "2026-11-24"],
            "snowfall_sum": [1, 2, 3, 4, 5],
            "weather_code": [3, 3, 3, 0, 71],
            "temperature_2m_max": [1, 2, 3, 4.4, 5],
            "temperature_2m_min": [-5, -4, -3, -2, -1],
        },
    }
    return [one] * n
