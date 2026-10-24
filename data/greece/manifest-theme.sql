-- Name and colours of the installable web app (PWA), as the admin's "Manifest theme" page would
-- set them. Colours: the header (theme) and the page background (splash screen).
INSERT INTO manifest_theme (cobrand, name, short_name, background_colour, theme_colour)
VALUES ('greece', 'FixMyStreets Ελλάδα', 'FixMyStreets', '#f3f5fa', '#0c1b33')
ON CONFLICT (cobrand) DO UPDATE
   SET name = EXCLUDED.name, short_name = EXCLUDED.short_name,
       background_colour = EXCLUDED.background_colour, theme_colour = EXCLUDED.theme_colour;
