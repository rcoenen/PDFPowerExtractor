# PDFPowerExtractor Examples

## The Problem Illustrated

Imagine you have a PDF application form that looks like this visually:

```
┌─────────────────────────────────────────────────┐
│ EMPLOYMENT APPLICATION FORM                      │
│                                                  │
│ 3.2 Employment Status                           │
│ ○ Full-time  ● Part-time  ○ Self-employed      │
│                                                  │
│ 3.3 Years of Experience                         │
│ ☐ 0-2 years  ☒ 3-5 years  ☐ 5-10 years        │
│                                                  │
│ 3.4 Preferred Work Location                     │
│ ☒ Remote  ☒ Hybrid  ☐ Office                   │
└─────────────────────────────────────────────────┘
```

### Traditional PDF Extraction Output:
```
EMPLOYMENT APPLICATION FORM
3.2 Employment Status
3.3 Years of Experience  
3.4 Preferred Work Location
○ Full-time
● Part-time
○ Self-employed
☐ 0-2 years
☒ 3-5 years
☐ 5-10 years
☒ Remote
☒ Hybrid
☐ Office
```

Notice how the questions and answers are completely separated? An AI reading this has no idea that "Part-time" is the answer to "Employment Status".

### PDFPowerExtractor Output:
```
EMPLOYMENT APPLICATION FORM

3.2 Employment Status
○ Full-time  ● Part-time  ○ Self-employed

3.3 Years of Experience
☐ 0-2 years  ☒ 3-5 years  ☐ 5-10 years

3.4 Preferred Work Location
☒ Remote  ☒ Hybrid  ☐ Office
```

Now the visual relationships are preserved! AI models can clearly understand:
- Employment Status = Part-time
- Years of Experience = 3-5 years
- Preferred Work Location = Remote AND Hybrid

This makes the form data actually usable for AI processing, automated workflows, and data extraction.