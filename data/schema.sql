CREATE TABLE measurements (
            dateutc         TEXT PRIMARY KEY,
            device          TEXT,
            station_id      TEXT,

            -- Roh (imperial)
            indoortempf     REAL,
            tempf           REAL,
            dewptf          REAL,
            windchillf      REAL,
            indoorhumidity  INTEGER,
            humidity        INTEGER,
            windspeedmph    REAL,
            windgustmph     REAL,
            winddir         INTEGER,
            absbaromin      REAL,
            baromin         REAL,
            rainin          REAL,
            dailyrainin     REAL,
            weeklyrainin    REAL,
            monthlyrainin   REAL,
            solarradiation  REAL,
            uv              INTEGER,

            -- Berechnet (metrisch)
            indoor_temp_c   REAL,
            temp_c          REAL,
            dewpoint_c      REAL,
            windchill_c     REAL,
            windspeed_kmh   REAL,
            windgust_kmh    REAL,
            abs_pressure_hpa REAL,
            pressure_hpa    REAL,
            rain_mm         REAL,
            daily_rain_mm   REAL,
            weekly_rain_mm  REAL,
            monthly_rain_mm REAL,

            -- Zusätzliche berechnete Werte (v2)
            feels_like_c    REAL,
            wind_dir_text   TEXT,
            beaufort        INTEGER,
            beaufort_text   TEXT,
            temp_diff_c     REAL,
            climate_advice  TEXT,
            frost_text      TEXT,
            solar_klux      REAL,

            -- Meta
            softwaretype    TEXT,
            date_local      TEXT
        );
CREATE INDEX idx_dateutc ON measurements (dateutc);
CREATE INDEX idx_date_local ON measurements (date_local);
CREATE TABLE csv_imports (
            filename TEXT PRIMARY KEY,
            mtime    REAL
        );
