from much_more_songs import *

my_runner = MuchMoreRunner()
my_data = my_runner.run('26R3e7bjY6e9dlgghide8L')

print(my_data)



#1C2QJNTmsTxCDBuIgai8QV  Resitance (Muse) --working
#26R3e7bjY6e9dlgghide8L Tea in the desert (Police) -- working
#54UFDHWI2q7WHfrGbSNWph Scentless Apprentice (Nirvana) -- working


#09ezgACZuwWZt6CtQSSLRG End of the Night (the Doors) -- extract only minor reference whike main reference not (main reference compare in both English and French)
#!!!!!! + Google Bard returns as output the explaination of how to build a pandas dataframe with entities and relations insted of creating one as it does with other cases

#2B17416FS7vL5qljgqfm7L Te Future is Now (The Offspring) -- extracts 1984 as reference but not "Orwell" (even if it is present in the annotations), however it gets high similarity score but not other scores so it is not included
# !!! + It finds another referece to a single by "The Dead Kennedys" that has no wikipedia page (raising an error) --> what to do? How to be sure that we are talking about a song here?

#1FPSkRkDlthbAceSIIWc4C Welcome Home (Sanitarium) (Metallica) -- refernce present in song description only
#75zMKn5euxQdlkZgu4P42J Sympathy for the devil (Rolling Stones) -- nothing found even if present referece to "The Master and Margherita" (the description also contains them)
#6KCjY5kHvgWaWcAV6BBzxO The Battle of Evermore (Led Zeppelin) -- nothing found even if present references to the Lord of the Rings (same for Ramble On)
#6K8ROjiPJqyHDJS0sA0dwH Rime of the ancient mariner (Iron Maiden) -- isrc not matching between spotify and musicbrainz
#4VqPOruhp5EdPBeR92t6lQ Muse Uprising -- no relation found (do not recognize 1984 and other Muse's songs cited in annotations)
#0tHbQRjL5phd8OoYl2Bdnd Muse United states of Eurasia -- no relation found (do not identify 1984)
#7ouMYWpwJ422jRcDASZB7P Muse Knights of Cydonia -- candidates scrores are too low to be included in the selceted entities
#4xkcGfpM9RwB4IiQ7yx2dB 2+2=5 Radiohead -- no relation receives enough score even if correct and some relations not found (1984 and Dante's Inferno)
#0Kt0khTz1EzjtaQI8A339S Starz in their eyes -- No relation found
#7xRemq7GLu0Tbqe9OckG87 The Man in Me (Dylan) -- No relation gets enough scre even if one is valuable

