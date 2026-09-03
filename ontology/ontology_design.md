# FIFA World Cup 2022 — Ontology Design

**Namespace:** `http://www.semanticweb.org/worldcup2022#` (prefix `wc:`)
**File:** `worldcup_tbox.ttl` (importable OWL schema — open directly in Protégé)

## Classes (10)

| Class | Meaning | Source data |
|---|---|---|
| `Tournament` | The 2022 World Cup edition | `tournament_2022.csv` |
| `Confederation` | UEFA, CONMEBOL, AFC, etc. | `teams_2022.csv` |
| `Team` | A national team (32) | `teams_2022.csv` + `standings_2022.csv` |
| `Player` | A squad player (831) | `players_2022.csv` + stats |
| `Club` | Player's club side | `player_stats_2022_clean.csv` |
| `Match` | A fixture (64) | `matches_2022.csv` |
| `Goal` | A goal event (172) | `goals_2022.csv` |
| `Stadium` | A venue (8) | `stadiums_2022.csv` |
| `Position` | GK / DF / MF / FW (enumerated individuals) | `squads_2022.csv` |
| `PlayerImage` | Multimedia: photo folder + feature vector | `image_index.csv` |

## Object properties (relationships)

| Property | Domain → Range |
|---|---|
| `belongsToConfederation` | Team → Confederation |
| `participatesIn` | Team → Tournament |
| `wonBy` | Tournament → Team |
| `representsTeam` | Player → Team |
| `playsForClub` | Player → Club |
| `hasPosition` | Player → Position |
| `hasImage` | Player → PlayerImage |
| `partOfTournament` | Match → Tournament |
| `hasHomeTeam` | Match → Team |
| `hasAwayTeam` | Match → Team |
| `playedAt` | Match → Stadium |
| `hasGoal` / `scoredInMatch` | Match ↔ Goal (inverse) |
| `scoredBy` | Goal → Player |
| `goalForTeam` | Goal → Team |

## Datatype properties (attributes)

- **Tournament:** tournamentName, year, startDate, endDate, hostCountry, numberOfTeams
- **Confederation:** confederationName, confederationCode
- **Team:** teamName, teamCode, federationName, regionName,
  finalPosition, gamesPlayed, wins, draws, losses, goalsFor, goalsAgainst,
  goalDifference, points  *(final-standings block from `FIFA - 2022.csv`)*
- **Player:** givenName, familyName, fullName, birthDate, shirtNumber, nationality,
  appearances, goalsScored, assistsProvided, dribblesPer90, interceptionsPer90,
  tacklesPer90, duelsWonPer90, savePercentage, cleanSheets
- **Club:** clubName
- **Match:** matchName, matchDate, stageName, groupName, homeScore, awayScore,
  extraTime, penaltyShootout, result
- **Goal:** minuteLabel, minuteRegulation, isPenalty, isOwnGoal
- **Stadium:** stadiumName, city, country, capacity
- **Position:** positionName, positionCode
- **PlayerImage:** folderPath, imageCount, featureVector

## Example instance pattern (what the ABox will look like)

```turtle
wc:player_messi a wc:Player ;
    wc:fullName "Lionel Messi" ; wc:shirtNumber 10 ;
    wc:representsTeam wc:team_ARG ;
    wc:playsForClub wc:club_paris_saint_germain ;
    wc:hasPosition wc:Forward ;
    wc:hasImage wc:img_messi .

wc:goal_0421 a wc:Goal ; wc:minuteRegulation 23 ; wc:isPenalty true ;
    wc:scoredBy wc:player_messi ; wc:goalForTeam wc:team_ARG ;
    wc:scoredInMatch wc:match_final .
```
