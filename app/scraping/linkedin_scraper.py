import json
import csv
import re
import time
from datetime import datetime
from urllib.parse import quote
import requests
from app.scraping.base_scraper import BaseScraper

# ─── Configuration ────────────────────────────────────────────────────────────
SEARCH_KEYWORDS  = "software engineering internship"
LOCATION         = "Tunisia"                                # <-- Change this to any country or city!
LIMIT            = 50                                       # Max results to fetch
DELAY_BETWEEN    = 1.5                                      # Seconds between detail fetches

OUTPUT_JSON = f"internships_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
OUTPUT_CSV  = f"internships_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
# ──────────────────────────────────────────────────────────────────────────────

class LinkedInScraper(BaseScraper):
    
    def __init__(self):
        super().__init__()
        
        # Centralized active session state tokens
        self.my_csrf_token = "ajax:7466672779380655529"
        
        # Base headers used to interact with LinkedIn's internal business layer
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/vnd.linkedin.normalized+json+2.1",
            "csrf-token": self.my_csrf_token,
            "X-Restli-Protocol-Version": "2.0.0",
            "Cookie": (
                'bcookie="v=2&d49786f8-cc4f-44d3-8a12-c59f72874640"; '
                'bscookie="v=1&20251124212601b2807295-4248-45e1-8db2-51bef75a1433AQE1v_ma4gBp-Nc2Mf8bt4nA-1hbybWg"; '
                'g_state={"i_l":0}; li_theme=light; li_theme_set=app; '
                'li_sugr=8eb953a5-52ca-46de-9789-68b3e01c9351; '
                'li_rm=AQEegsN5Hmzk7wAAAZr_tVwnAe6qCVuR2dufORzv_nL4fbasIjx_yJAAsPbjIRmf5UYgi_WEK1RsnU-h80E_ser3fcC8fwBYBRII_9GYMAjH-q4u7dYws6QwvSJvLiBpVEj1l1vg1ySULVn-vN_kqQkL5tREdsFh5bzv2mpA4an6fHCIjtyeM74QuQQJCchI83IjH1T9lKamzU0EGb1afs0cUShDgdi7bVYYcBu0GhswG2tdR95Lw8s-s8jG-yFo380YON-Q_8oUCBp6r3OULGRTUQnJ8kZhFRcFguDLeLxi7tmR3kM0vxK9Q3fgUJclKN2X7YWgsC--tsjlrgHrxw; '
                'visit=v=1&M; timezone=Africa/Tunis; aam_uuid=19233138019725140470624005677551555753; '
                '_gcl_au=1.1.1710655679.1779011099; _pxvid=57ddb537-5381-11f1-b7d8-e562bbfc35c1; '
                'dfpfpt=2e375b59f2e94087ba683112816467ff; AMCVS_14215E3D5995C57C0A495C55%40AdobeOrg=1; '
                'lang=v=2&lang=fr-fr; liap=true; '
                'li_at=AQEDAVvBZe4EiPVJAAABnnQZ7EwAAAGemCZwTE0AGHnTBx3JYHFl_uFVw5CzFvd4Kh8LQfGxUJzwXWU8DRYxko-HdRg_OedcjHY1Ef_kLFZbXwq1SxySEwqTSjTRLUkkzjuRUi5Wt4MOT4_kVpncC3JU; '
                f'JSESSIONID="{self.my_csrf_token}"; '
                'sdui_ver=sdui-flagship:0.1.41738+SduiFlagship0; '
                'AnalyticsSyncHistory=AQL8kt9Ok9OOlAAAAZ6HUa1HvvwTe_lk9Ir60oiJudkHpzv18LT5l5z1GYLr6Il1Rs2E9lCS21XLwK_6yxMOwg; '
                'lms_ads=AQFq_M1VgpRReQAAAZ6HUbADzY8_8mZP2PzgVmwMO-pu7J_gfCZ6zRFKV39WAO4WuMoUIpnAVLfAaKMe0uzgqxLaV6JHugzc; '
                'lms_analytics=AQFq_M1VgpRReQAAAZ6HUbADzY8_8mZP2PzgVmwMO-pu7J_gfCZ6zRFKV39WAO4WuMoUIpnAVLfAaKMe0uzgqxLaV6JHugzc; '
                '_guid=a89801a2-4c3f-4e3d-83fc-c0695200dff0; lidc="b=VB98:s=V:r=V:a=V:p=V:g=3603:u=3:x=1:i=1780388786:t=1780473132:v=2:sig=AQHGOJGLUBJqN3d_QN_azqnbmU1h3FKI"; '
                '__cf_bm=mmh4Af9A6RCbsne3rwaRAbxfuSSPQ41tujF1oQChg_4-1780389438.2393534-1.0.1.1-pe5G3GtA2h2ptcXPFFdm7.HzUIRt849mmUpsezZxjFAFOE.T2CMvXCLBt7mb.Pw8YvY7r32mN_osA4RHMu0blLCx7UMX_CwhTb.ajoSrwOdbgDcXpjI_1ZV04V8Ror1_'
            )
        }

    def fetch_linkedin_job_ids(self, keyword: str, location_name: str, total_jobs_to_fetch: int) -> list:
        """Step 1: Scrape the list of unique job IDs from search cards using dynamic geoId mapping."""
        base_url = "https://www.linkedin.com/voyager/api/voyagerJobsDashJobCards"
        all_job_ids = set()
        encoded_keyword = quote(keyword)
        
        for start_index in range(0, total_jobs_to_fetch, 25):
            target_url = (
                f"{base_url}?"
                f"decorationId=com.linkedin.voyager.dash.deco.jobs.search.JobSearchCardsCollection-220&"
                f"count=25&"
                f"q=jobSearch&"
                f"query=(origin:JOB_SEARCH_PAGE_SEARCH_BUTTON,"
                f"keywords:{encoded_keyword},"
                f"locationUnion:(seoLocation:(location:{location_name})),"
                f"selectedFilters:(sortBy:List(R),experience:List(1,2))," 
                f"spellCorrectionEnabled:true)&"                                                 
                f"start={start_index}"                                                                    
            )
            try:
                response = requests.get(target_url, headers=self.headers)
                if response.status_code == 200:
                    found_ids = re.findall(r"jobPosting:(\d+)", response.text)
                    all_job_ids.update(found_ids)
                else:
                    print(f"  ⚠️ Error fetching pass {start_index}: HTTP {response.status_code}")
                    break
            except Exception as e:
                print(f"  ⚠️ Search Error during index pass: {e}")
                break

        return list(all_job_ids)[:total_jobs_to_fetch]
    
    def get_top_card(self, payload: dict) -> dict:
        """Safely isolates the topCard configuration dict from the GraphQL payload elements list."""
        try:
            elements = payload.get("data", {}).get("jobsDashJobPostingDetailSectionsByCardSectionTypes", {}).get("elements", [])
            for element in elements:
                for section in element.get("jobPostingDetailSection", []):
                    if "topCard" in section and section["topCard"] is not None:
                        return section["topCard"]
        except (KeyError, AttributeError):
            pass
        return {}

    def fetch_company_master_record(self, payload: dict) -> dict:
        """Extract company profile record from the nested dictionary tree."""
        top_card = self.get_top_card(payload)
        return top_card.get("jobPosting", {}).get("companyDetails", {}).get("jobCompany", {}).get("company", {})

    def extract_job_subtitles(self, payload: dict) -> dict:
        """Extract job subtitles and titles from topCard directly."""
        top_card = self.get_top_card(payload)
        if top_card:
            return {
                "summary_line": top_card.get("navigationBarSubtitle"),
                "display_title": top_card.get("jobPostingTitle")
            }
        return {}

    def fetch_job_details(self, job_id: str) -> dict:
        """Step 2: Pull specific detailed data metrics matching the exact template output schema."""
        base_url = "https://www.linkedin.com/voyager/api/graphql"
        query_id = "voyagerJobsDashJobPostingDetailSections.2bf6cded247cb2f6cc7dcda5558af592"
        variables = f"(cardSectionTypes:List(TOP_CARD,HOW_YOU_FIT_CARD),jobPostingUrn:urn%3Ali%3Afsd_jobPosting%3A{job_id},includeSecondaryActionsV2:true,jobDetailsContext:(isJobSearch:true))"
        
        target_url = f"{base_url}?variables={variables}&queryId={query_id}"
        
        details_headers = self.headers.copy()
        details_headers["Accept"] = "application/json"
        
        job_data = {
            "job_id": job_id,
            "title": "Unknown Title",
            "company": "Unknown Company",
            "location": LOCATION,  
            "posted_at": datetime.now().strftime("%Y-%m-%d %H:%M"), 
            "remote": False,
            "apply_url": f"https://www.linkedin.com/jobs/view/{job_id}",
            "description_snippet": "",
            "description_full": ""
        }
        
        try:
            response = requests.get(target_url, headers=details_headers)
            if response.status_code == 200:
                payload_dict = response.json()
                
                # Use integrated class utilities to evaluate elements
                company_record = self.fetch_company_master_record(payload_dict)
                subtitles = self.extract_job_subtitles(payload_dict)
                
                # Apply dynamic parsed elements onto baseline schema dict
                if company_record.get("name"):
                    job_data["company"] = company_record.get("name")
                elif subtitles.get("summary_line"):
                    # Quick extraction split if baseline profile records fall through
                    job_data["company"] = subtitles.get("summary_line").split("·")[0].strip()
                
                if subtitles.get("display_title"):
                    job_data["title"] = subtitles.get("display_title")

                # Fallback Regex Extractions for descriptions and attributes
                response_text = response.text
                location_matches = re.findall(r'"formattedLocation":"([^"]+)"', response_text)
                if location_matches:
                    job_data["location"] = location_matches[0]
                
                if '"workRemoteAllowed":true' in response_text or '"workPlaceIndicator":"REMOTE"' in response_text:
                    job_data["remote"] = True
                
                all_text_blocks = re.findall(r'"text":"([^"]+)"', response_text)
                if all_text_blocks:
                    longest_block = max(all_text_blocks, key=len)
                    clean_desc = longest_block.replace("\\n", "\n").replace('\\"', '"')
                    job_data["description_full"] = clean_desc
                    job_data["description_snippet"] = clean_desc[:500].replace("\n", " ")
            else:
                print(f"  ⚠️ Could not fetch details for job {job_id}: Status {response.status_code}")
        except Exception as e:
            print(f"  ⚠️ Could not fetch details for job {job_id}: {e}")
            
        return job_data

    def scrape(self) -> list:
        """Main orchestrator block managing execution output and logging layout frames."""
        print("╔══════════════════════════════════════════════════════╗")
        print("║        LinkedIn Internship Scraper Framework         ║")
        print("╚══════════════════════════════════════════════════════╝\n")
        
        print(f"🔍 Searching: '{SEARCH_KEYWORDS}' | Target Area: {LOCATION} | Type: Internship")
        print(f"   Limit: {LIMIT} | Active Headers Inject Mode: True\n")
        
        job_ids = self.fetch_linkedin_job_ids(SEARCH_KEYWORDS, LOCATION, LIMIT)
        total_found = len(job_ids)
        
        if not job_ids:
            print("⚠️ No results returned. Check cookie/session expiration bounds.")
            return []
            
        print(f"📋 Found {total_found} listings. Fetching details…\n")
        
        completed_jobs = []
        
        for idx, j_id in enumerate(job_ids, start=1):
            job_details = self.fetch_job_details(j_id)
            
            print(f"   [{idx:02d}/{total_found}] {job_details['title']} @ {job_details['company']}")
            completed_jobs.append(job_details)
            
            time.sleep(DELAY_BETWEEN)
            
        # ── Write JSON Document Output ──────────────────────────────────────────
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(completed_jobs, f, ensure_ascii=False, indent=2)
        print(f"\n✅ JSON saved → {OUTPUT_JSON}")
        
        # ── Write CSV Document Output ───────────────────────────────────────────
        csv_fields = ["job_id", "title", "company", "location", "posted_at",
                      "remote", "apply_url", "description_snippet"]
        
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(completed_jobs)
        print(f"✅ CSV  saved → {OUTPUT_CSV}")
        
        print(f"\n🎉 Done! {len(completed_jobs)} internships scraped.")
        return completed_jobs

if __name__ == "__main__":
    scraper = LinkedInScraper()
    scraper.scrape()