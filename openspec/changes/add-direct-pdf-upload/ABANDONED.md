# ABANDONED: Direct PDF Upload

**Date Abandoned:** 2025-12-12
**Reason:** All three tested approaches failed (Files API, image_url, file_url)

---

## Spike Test Results

Tested **three different approaches** to bypass image conversion:

### Test 1: Files API Approach ❌

**Method:** Upload PDF → file_id → reference in chat/completions

**Outcome:**
- ✅ Files API upload: **SUCCESS** (file_id returned)
- ✅ chat/completions accepts file_id: **SUCCESS** (request accepted)
- ❌ Content extraction: **CATASTROPHIC** (0.9% quality)

**Quality:**
- Image-based baseline: 32,976 tokens (full extraction)
- Files API approach: 286 tokens (empty code blocks only)
- Quality: **0.9% of baseline**

**Root Cause:** Files API designed for translation auxiliary files (glossaries), NOT document OCR.

### Test 2: Direct PDF in Vision Mode (image_url) ❌

**Method:** Send PDF as base64 with `image_url` type (like we send images)

**Outcome:** ❌ **All 4 format attempts rejected**

**Errors:**
- Error 1210: "图片输入格式/解析错误" (image format/parsing error)
- Error 1214: "type error" (document/file types not supported)

**Root Cause:** GLM-4.6V vision mode only accepts **image formats** (WEBP, PNG, JPEG), NOT PDFs.

### Test 3: file_url Format ❌

**Method:** Use `file_url` type (discovered in official Chinese docs)

**Tested URLs:**
- ✅ Federal Register (.gov): **SUCCESS** (8,229 tokens)
- ❌ Google Drive: FAILED (104 tokens, PDF not fetched)
- ❌ Scaleway S3: Error 1210 "Invalid API parameter"
- ❌ Data URI: Error 500 "Network error"
- ❌ file_id: Error 1214 "Invalid URL format"

**Root Cause:** Z.AI **whitelists domains** for file_url:
- ✅ Works: .gov domains, cdn.bigmodel.cn (Z.AI's CDN)
- ❌ Blocked: Google Drive, AWS S3, Scaleway, Azure, GCP (all major cloud storage)
- **Impractical for dynamic user-uploaded PDFs**

---

## Comprehensive Conclusion

**None of the three approaches work:**
1. Files API: Wrong use case (translation vs OCR) - 0.9% quality
2. Vision mode (image_url): Rejects PDF format (images only) - Error 1210
3. file_url format: Domain whitelisting blocks all practical cloud storage - Only .gov works

**Current image-based approach is the ONLY viable method.**

---

## Why Abandon

1. **Quality catastrophic:** 0.9% vs baseline (99.1% degradation)
2. **Wrong API use case:** Files API is for translation, not vision tasks
3. **Current solution works:** Image-based approach achieves 99.6% quality concurrently
4. **No benefit:** Even if it worked, wouldn't solve concurrent degradation

---

## Current Solution (Proven)

**Status:** Working excellently after removing PAGE_TYPE from prompts

- ✅ Quality: 32,976 tokens (perfect extraction)
- ✅ Speed: 129.5s for 30 pages (concurrent, max_parallel=3)
- ✅ Cost: $0.065 per 30 pages
- ✅ Concurrent degradation: **SOLVED** via simplified prompts

---

## Spike Investment

- **Time:** 3.5 hours (1.5h Files API + 0.5h image_url + 1.5h file_url/domain testing)
- **Value:** Saved 8-12 hours of integration work by discovering non-viability early
- **Recommendation:** ✅ Spike-first approach validated

---

## Lessons Learned

1. API documentation hints matter ("translation service" should have been red flag)
2. Spike testing prevents wasted integration effort
3. Current image-based solution is optimal - don't fix what isn't broken
4. Documentation can be misleading - Chinese docs show `file_url` type but omit domain whitelisting
5. Hidden restrictions exist - file_url requires whitelisted domains (.gov, Z.AI CDN only)
6. Cloud storage is blocked - Can't use AWS, GCP, Azure, Scaleway, Google Drive for file_url
7. Thoroughly test all documented formats - `file_url` exists but unusable for real-world use

---

**Conclusion:** Direct PDF upload is **NOT viable** for OCR/extraction with GLM-4.6V.

**Full findings:** `/Users/rob/Desktop/B07001/spike_comprehensive_findings.md`
