Should it just serialize/deserialize the whole game state for save files?

Are they just going to stick the old mentor's dialogue around forever?

Can we redesign the game so python backend APIs, then either pygame frontend or webapp frontend renders the game on top of that?



If you want, next I can do the follow-up parity pass: enforce context-town/context-world/context-any restrictions at cast time and map specific iconic spells to more source-authentic effects.

When doing the above, please update the UI to show a different color for spells not available in the current context.

Add a searchbar to the spellbook modal. And to the reagent modal, if we'll ever have that many reagents...


Are we able to draw the spellbook modal dialogue to look like a book?
Draw the reagents modal to look like an alchemy bag?
Draw the inventory modal to look like a chest?

IDK.



Spellbook modal:
- Spells blocked due to missing a reagent should have an icon indicating that.
- Spells blocked due to not being available in the current context should have an icon indicating that.
This is more robust than just color. Red color can indicate not able to. Icon can indicate the reason(s) why.
Just color is stuck to one reason. Icons can show it's missing a reagent AND it's not available in the current context.
In the header at the top, can include the icon next to the blocked reason too. Right now it's just acting as a color-coded key/legend.
