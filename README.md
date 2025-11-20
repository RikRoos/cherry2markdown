# `cherry2md.py` - converter Cherrytree notes to markdown 

Cherry2md is a utility for converting Cherrytree notes to _markdown_. The tool also converts attachments (e.g., images) from Cherrytree XML to PNG and inserts the image link at the appropriate location in your notes. 

## A Foreword

For a long time I took notes using Cherrytree. At some point in time, more and more “fancy” Markdown-based note-taking apps started to appear. To switch over, I first needed to convert my existing notes from XML to Markdown. Cherrytree offers several export formats, but none of them produce markdown files with full support for links and images.

One option is to export an HTML dump from Cherrytree. In theory, that can be converted to Markdown. However, over the years I had used Cherrytree’s markup tools in many different and inconsistent ways. I realized I could devise some export logic with a handful of rules, but I would need to build it myself. And so I did. The result is this Python library.

Overall, it required quite a bit of effort, as there was always some small deviation from earlier observations.

At that time, I had not yet switched to Obsidian. That’s unfortunate, because I could have taken Obsidian’s Markdown style and other conventions into account from the beginning. For example, I had no reason to expect that Obsidian’s tree structure always starts with folders and only then lists the individual notes. But in the end, anything was better than using multiple note-taking tools side by side. That said, I added some Obsidian-specific optimizations toward the end of the project, as I had already switched to using Obsidian for new notes.

I wrote a userguide to explain the features of cherry2md, you can find it here: [userguide cherry2md](https://github.com/rikroos/cherry2markdown/blob/master/USERGUIDE.md)

##  My Advice

Start with a few test runs and inspect the results carefully in your note-taking app. You may find certain behaviors you want to adjust in the source.

Also take a close look at the TOML configuration file and study the results it produces. Review the CLI parameters of the program (`cherry2md.py`) Python runner as well, these can help a lot by analyzing the output.

It may also be helpful to use the option that exports **all notes into one large file**. With a text editor you can then search for the output of specific notes. This can be more convenient than using text processing tools like *grep* or *ripgrep* across the exported directory tree. Another advantage is that you can do a *diff* on these large output files after making changes to the configuration or source code. Sometimes a modification can improve the layout of some notes but can also make other notes worse; with a *diff* this can be spotted more easily.

If you have created nodes in Cherrytree that each cover a distinct topic, consider exporting those nodes separately. This allows you to easily create separate Obsidian vaults. One advantage is that searches for specific terms will not return notes from unrelated topics.

Another tip: each exported note ends with a  small comment containing the export date and the original Cherrytree ID. In Cherrytree, you can use that ID to locate the corresponding note. See the TOML file for more details on this behavior.

*The author, November 2025*

