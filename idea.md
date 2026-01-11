I'm using Bactora OS (docs: https://wiki.batocera.org/start) on a raspberry pi 5. 

Already downloaded and set up many ROMS, however many of them don't have the meta data (some of them were added by scraping using Bactora's built in scraper: https://wiki.batocera.org/scrape_from)

My idea is to create a script that can automatically fetch and add missing metadata (like game title, release year, genre, developer, cover art, screenshot, video, etc.) for the ROMs that lack this information and add them in the proper file structure for Bactora OS to recognize.

The drive is connected through network share and I'm on Mac, but we can maybe make it a bactora app or a docker container that can run on the pi itself. but with tests done on mac first.

Sources for metadata can be from various online databases like TheGamesDB, IGDB, or MobyGames, screenscraper.fr (https://screenscraper.fr/webapi2.php?alpha=0&numpage=0), or even Wikipedia, if not available from the game databases.


The script should do the following:

Game Management:
1. Scan the ROMs directory to identify games missing metadata.
2. Find duplicates and handle them appropriately (e.g., keep the one with the most complete metadata, or ask).
3. file name sanitization to improve matching with online databases (e.g., removing special characters, standardizing naming conventions).
   

Metadata Fetching/Scraping:
1. Scan the ROMs directory to identify games missing metadata.
2. For each identified game, query the selected online databases to fetch the relevant metadata.
3. Download and save cover art, screenshots, and videos to the appropriate directories.
4. Update the ROMs' metadata files with the fetched information in the format recognized by Bactora OS.
5. Log the changes made and any errors encountered during the process.
6. Make sure in case of error we can resume from where we left off.
7. provide a simple user interface (CLI or web-based) to allow users to configure settings like which databases to use, paths, etc.
8. Optionally, implement a scheduling feature to run the script periodically to check for new ROMs or updates.


--------------------


In each ROM folder (each emulator), there's a gamelist.xml file that contains the metadata, sample:

```xml
...
	<game>
		<path>./PSX - Grand Theft Auto 2/Grand Theft Auto 2.cue</path>
		<name>Grand Theft Auto 2</name>
		<image>./images/Grand Theft Auto 2-image.png</image>
		<marquee>./images/Grand Theft Auto 2-marquee.png</marquee>
		<thumbnail>./images/Grand Theft Auto 2-thumb.png</thumbnail>
		<releasedate>19991025T000000</releasedate>
		<developer>Rockstar North</developer>
		<publisher>Rockstar Games</publisher>
		<genre>Course</genre>
		<players>1</players>
		<favorite>true</favorite>
		<playcount>2</playcount>
		<lastplayed>20260109T000400</lastplayed>
		<gametime>2113</gametime>
		<lang>en</lang>
		<scrap name="HfsDB" date="20260106T115650" />
	</game>
	<game>
		<path>./Oddworld - Abe's Oddysee (USA)/Oddworld - Abe's Oddysee (USA).cue</path>
		<name>Oddworld - Abe'S Oddysee</name>
		<desc>Odd alien Abe has worked for years as a slave at a futuristic meat packing plant called Rupture Farms. Though the plant prides itself on producing Paramite Pies and Scarab Cakes, the species the food is made from is on the verge of extinction. Using a full-fledged alien race as ingredients, the owners have come up with a new product called Mudokon Pops.</desc>
		<image>./images/Oddworld - Abe's Oddysee (USA)-image.png</image>
		<marquee>./images/Oddworld - Abe's Oddysee (USA)-marquee.png</marquee>
		<thumbnail>./images/Oddworld - Abe's Oddysee (USA)-thumb.jpg</thumbnail>
		<releasedate>19970918T000000</releasedate>
		<developer>GT Interactive</developer>
		<publisher>Oddworld Inhabitants</publisher>
		<genre>Plate-formes</genre>
		<players>2</players>
		<favorite>true</favorite>
		<playcount>1</playcount>
		<lastplayed>20260109T190818</lastplayed>
		<gametime>2096</gametime>
		<lang>en</lang>
		<region>us</region>
		<scrap name="HfsDB" date="20260106T115856" />
	</game>
</gameList>
```

Also check their docs for complete structure and tags: https://wiki.batocera.org/menu_tree#scrape

I have most popular emulators set up, like NES, SNES, PSX, N64, Sega Genesis, etc. The script should be flexible enough to handle different emulators and their specific metadata requirements.

ROMS: around 100-1000 per emulator

----
2. yes, the standard bactora file structure is like this ():
/sources/roms/nes/game1.zip
/sources/roms/nes/gamelist.xml


3. I have API credentials for screenscraper.fr if needed. If anything else is needed let me know and I'll create it, ideally free.

4. SMB path (\\BATOCERA\share), I can also have access to the pi via ssh if needed.

5. interactive prompts for each duplicate with the option to select default action (keep first, keep most complete, skip, etc.)

6. let's go the full feature, you can leave the scheduler to last if needed.
7. python seems like a good choice, check out the batocera scraper and also the Batecero scripts (https://wiki.batocera.org/launch_a_script) maybe we can implement it as a bactora script later on.

8. all that needed, video can be additional tag (and make sure it works with bactora video playback in gamelist.xml)


-------------------------

1. user credentials

2. study bactoria roms structure and gamelist.xml format, it follows that, most of the roms are in zip files, some others are in folders (like psx with cue/bin files)
3. study the online databases api (screenscraper.fr first, then others if needed)
   - try to find best matching strategy (by name, by release year, etc.), if not found try alternative names (like removing special characters, etc.) - no region preference, USA is good 
4. usa unless specified in the filename (like (EUR), (JPN), etc.)
5. yes good idea, create a _tempcopy copy
6. see the screenshot and also @roms folder in this directory for a psx sample.


