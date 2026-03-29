import { useEffect,useState } from "react";
import {
  listProjects,
  createReport,
  listReports,
  getReport,
  exportPortfolio,
  generatePortfolioDetailsForReport,
  getPortfolio,
  setPrivacyConsent,
  publishPortfolio,
  unpublishPortfolio,
  updatePortfolioProject,
  getBadgeProgress,
} from "../api/client";

const OP_STATE={
  IDLE:"idle",
  LOADING:"loading",
  GENERATING:"generating",
  EXPORTING:"exporting",
  SAVING:"saving",
  TOGGLING_MODE:"toggling_mode",
};

function formatBadgeLabel(badgeId=""){
  return badgeId.split("_").map((chunk)=>chunk.charAt(0).toUpperCase()+chunk.slice(1)).join(" ");
}

function badgeEarnedForProject(badge,projectName){
  const tracked=badge?.project?.name;
  if(!tracked||!projectName)return false;
  return `${tracked}`.trim().toLowerCase()===`${projectName}`.trim().toLowerCase()&&!!badge.earned;
}

function escapeHtml(value=""){
  return String(value)
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#39;");
}

function PortfolioPage() {
  const [loading,setLoading]=useState(false);
  const [opState,setOpState]=useState(OP_STATE.IDLE);
  const [message,setMessage]=useState("");
  const [messageType,setMessageType]=useState("info");
  const [projects,setProjects]=useState([]);
  const [selectedProjectIds,setSelectedProjectIds]=useState([]);
  const [reports,setReports]=useState([]);
  const [selectedReport,setSelectedReport]=useState(null);
  const [reportTitle,setReportTitle]=useState("My Portfolio Report");
  const [reportNotes,setReportNotes]=useState("");
  const [portfolio,setPortfolio]=useState(null);
  const [openProjects,setOpenProjects]=useState({});
  const [projectDrafts,setProjectDrafts]=useState({});
  const [searchText,setSearchText]=useState("");
  const [languageFilter,setLanguageFilter]=useState("all");
  const [collabFilter,setCollabFilter]=useState("all");
  const [badgeProgress,setBadgeProgress]=useState([]);
  const [copyToastVisible,setCopyToastVisible]=useState(false);

  useEffect(()=>{loadInitialData();},[]);

  function setStatus(nextMessage,nextType="info"){
    setMessage(nextMessage);
    setMessageType(nextType);
  }

  function showCopyToast(){
    setCopyToastVisible(true);
    window.clearTimeout(window.__portfolioCopyToastTimer);
    window.__portfolioCopyToastTimer=window.setTimeout(()=>setCopyToastVisible(false),2200);
  }

  async function loadInitialData(){
    setLoading(true);
    setOpState(OP_STATE.LOADING);
    setStatus("");
    try{
      const [projectData,reportData,badgeData]=await Promise.all([listProjects(),listReports(),getBadgeProgress()]);
      const allProjects=projectData.projects??[];
      setProjects(allProjects);
      setBadgeProgress(badgeData?.badges??[]);
      setSelectedProjectIds(allProjects.map((p)=>p.id));

      const filteredReports=(reportData.reports??[]).filter((r)=>(r.report_kind??"resume")==="portfolio");
      setReports(filteredReports);

      if(selectedReport?.id){
        const refreshed=filteredReports.find((r)=>r.id===selectedReport.id);
        setSelectedReport(refreshed??selectedReport);
      }
    }catch(e){
      setStatus(e.message??"Failed to load portfolio page data","error");
    }finally{
      setLoading(false);
      setOpState(OP_STATE.IDLE);
    }
  }

  function toggleProject(id){
    setSelectedProjectIds((prev)=>prev.includes(id)?prev.filter((projectId)=>projectId!==id):[...prev,id]);
  }

  function togglePortfolioProject(key){
    setOpenProjects((prev)=>({...prev,[key]:!prev[key]}));
  }

  function buildDraftFromProject(project){
    const custom=project?.portfolio_customizations??{};
    const details=project?.portfolio_details??{};
    return {
      custom_title:(custom.custom_title??"").trim(),
      custom_overview:(custom.custom_overview??details.overview??project?.summary??"").trim(),
      custom_achievements:Array.isArray(custom.custom_achievements)
        ? custom.custom_achievements.join("\n")
        : Array.isArray(details.achievements)
        ? details.achievements.join("\n")
        : (project?.bullets??[]).join("\n"),
      is_hidden:!!custom.is_hidden,
    };
  }

  function hydrateDrafts(nextPortfolio){
    const drafts={};
    (nextPortfolio?.projects??[]).forEach((p)=>{drafts[p.project_name]=buildDraftFromProject(p);});
    setProjectDrafts(drafts);
  }

  function handleDraftChange(projectName,field,value){
    setProjectDrafts((prev)=>({...prev,[projectName]:{...(prev[projectName]??{}),[field]:value}}));
  }

  function getDraft(projectName){
    return projectDrafts[projectName]??{
      custom_title:"",
      custom_overview:"",
      custom_achievements:"",
      is_hidden:false,
    };
  }

  function getRenderedTitle(project){
    const draft=getDraft(project.project_name);
    const v=(draft.custom_title??"").trim();
    return v||project?.project_name||"Untitled Project";
  }

  function getRenderedOverview(project){
    const draft=getDraft(project.project_name);
    const draftVal=(draft.custom_overview??"").trim();
    if(draftVal)return draftVal;
    const customVal=(project?.portfolio_customizations?.custom_overview??"").trim();
    if(customVal)return customVal;
    const detailsVal=(project?.portfolio_details?.overview??"").trim();
    if(detailsVal)return detailsVal;
    return (project?.summary??"No project summary available.").trim();
  }

  function getRenderedAchievements(project){
    const draft=getDraft(project.project_name);
    const fromDraft=(draft.custom_achievements??"").split("\n").map((x)=>x.trim()).filter(Boolean);
    if(fromDraft.length)return fromDraft;
    const custom=project?.portfolio_customizations?.custom_achievements;
    const fromCustom=Array.isArray(custom)?custom.map((x)=>`${x}`.trim()).filter(Boolean):[];
    if(fromCustom.length)return fromCustom;
    const fromDetails=Array.isArray(project?.portfolio_details?.achievements)?project.portfolio_details.achievements:[];
    if(fromDetails.length)return fromDetails;
    return (project?.bullets??[]).filter(Boolean);
  }

  function buildPortfolioHtml(projectList){
    const title=escapeHtml(portfolio?.title||"Portfolio");
    const cards=projectList.map((project)=>{
      const details=project?.portfolio_details??{};
      const renderedTitle=escapeHtml(getRenderedTitle(project));
      const renderedOverview=escapeHtml(getRenderedOverview(project));
      const renderedAchievements=getRenderedAchievements(project).map((x)=>`<li>${escapeHtml(x)}</li>`).join("");
      const contributorRoles=details?.contributor_roles??[];
      const contributorsHtml=contributorRoles.length
        ? `<h4>Contributors</h4><ul>${contributorRoles.map((c)=>`<li>${escapeHtml(c.name)}${c.role?` — ${escapeHtml(c.role)}`:""}</li>`).join("")}</ul>`
        : "";
      const roleLine=`${escapeHtml(details?.role||"Contributor")} • ${escapeHtml(details?.timeline||"Timeline unavailable")}`;

      return `
<section class="portfolio-card">
  <h3>${renderedTitle}</h3>
  <p class="meta">${roleLine}</p>
  <p>${renderedOverview}</p>
  ${renderedAchievements?`<h4>Key contributions</h4><ul>${renderedAchievements}</ul>`:""}
  ${contributorsHtml}
</section>`.trim();
    }).join("\n");

    return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>${title}</title>
<style>
  body{font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:920px;margin:32px auto;padding:0 16px;line-height:1.55;color:#111;}
  h1{font-size:2rem;margin:0 0 20px;}
  .portfolio-card{border:1px solid #ddd;border-radius:10px;padding:16px 18px;margin-bottom:14px;background:#fff;}
  .meta{color:#555;font-size:.95rem;margin-top:-4px;}
  h3{margin:0 0 8px;}
  h4{margin:12px 0 6px;font-size:1rem;}
  ul{margin:6px 0 0 20px;}
</style>
</head>
<body>
  <h1>${title}</h1>
  ${cards}
</body>
</html>`;
  }

  async function handleCopyPortfolioHtml(){
    if(!portfolio){
      setStatus("Generate a portfolio first.","error");
      return;
    }
    try{
      const html=buildPortfolioHtml(visiblePortfolioProjects);
      await navigator.clipboard.writeText(html);
      showCopyToast();
      setStatus("Portfolio HTML copied to clipboard.","success");
    }catch(e){
      setStatus("Clipboard copy failed. Your browser may block clipboard access.","error");
    }
  }

  async function handleCreateReport(){
    setLoading(true);
    setOpState(OP_STATE.LOADING);
    setStatus("");
    try{
      await setPrivacyConsent(true);
      if(!selectedProjectIds.length){
        setStatus("Select at least one project first.","error");
        return;
      }

      const created=await createReport({
        title:reportTitle,
        sort_by:"resume_score",
        notes:reportNotes,
        report_kind:"portfolio",
        project_ids:selectedProjectIds,
      });

      const createdReport=created.report??null;
      setSelectedReport(createdReport);
      setStatus(`Created report "${createdReport?.title??"Untitled"}"`,"success");
      await loadInitialData();

      if(createdReport?.id){
        await handleSelectReport(createdReport.id);
        const response=await getPortfolio(createdReport.id);
        const currentMode=(response?.portfolio?.portfolio_mode??"").toLowerCase();
        if(currentMode!=="public"){
          await publishPortfolio(createdReport.id);
        }
      }
    }catch(e){
      setStatus(e.message??"Failed to create report","error");
    }finally{
      setLoading(false);
      setOpState(OP_STATE.IDLE);
    }
  }

  async function handleSelectReport(id){
    setLoading(true);
    setOpState(OP_STATE.LOADING);
    setStatus("");
    setPortfolio(null);
    setOpenProjects({});
    setProjectDrafts({});
    try{
      const data=await getReport(id);
      setSelectedReport(data.report??null);
      setStatus("Report selected. Generate web portfolio to view sections.","info");
    }catch(e){
      setStatus(e.message??"Failed to load report","error");
    }finally{
      setLoading(false);
      setOpState(OP_STATE.IDLE);
    }
  }

  async function handleExportPortfolioPdf(){
    if(!selectedReport?.id){setStatus("Select or create a report first.","error");return;}
    setLoading(true);
    setOpState(OP_STATE.EXPORTING);
    setStatus("Exporting portfolio PDF...","info");
    try{
      const exp=await exportPortfolio({report_id:selectedReport.id,output_name:"portfolio.pdf"});
      window.open(`http://localhost:8000${exp.download_url}`,"_blank");
      setStatus("Portfolio PDF export started. Your download should open in a new tab.","success");
    }catch(e){
      setStatus(e.message??"Failed to export portfolio","error");
    }finally{
      setLoading(false);
      setOpState(OP_STATE.IDLE);
    }
  }

  async function handleGenerateWebPortfolio(){
    if(!selectedReport?.id){setStatus("Select or create a report first.","error");return;}
    setLoading(true);
    setOpState(OP_STATE.GENERATING);
    setStatus("Generating web portfolio sections...","info");
    setPortfolio(null);
    setOpenProjects({});
    setProjectDrafts({});
    try{
      await setPrivacyConsent(true);
      const names=projects.filter((p)=>selectedProjectIds.includes(p.id)).map((p)=>p.name).filter(Boolean);
      if(!names.length){setStatus("Select at least one project first.","error");return;}
      await generatePortfolioDetailsForReport({report_id:selectedReport.id,project_names:names});
      const response=await getPortfolio(selectedReport.id);
      const nextPortfolio=response?.portfolio??null;
      setPortfolio(nextPortfolio);
      hydrateDrafts(nextPortfolio);

      const initialOpen={};
      (nextPortfolio?.projects??[]).forEach((p,idx)=>{initialOpen[`${p?.project_name??"project"}-${idx}`]=idx===0;});
      setOpenProjects(initialOpen);
      setStatus("Web portfolio generated successfully.","success");
    }catch(e){
      setStatus(e.message??"Failed to generate web portfolio","error");
    }finally{
      setLoading(false);
      setOpState(OP_STATE.IDLE);
    }
  }

  async function handleSaveProjectCustomization(projectName){
    if(!selectedReport?.id){setStatus("Select a report first.","error");return;}
    const draft=getDraft(projectName);
    const payload={
      custom_title:(draft.custom_title??"").trim(),
      custom_overview:(draft.custom_overview??"").trim(),
      custom_achievements:(draft.custom_achievements??"").split("\n").map((x)=>x.trim()).filter(Boolean),
      is_hidden:!!draft.is_hidden,
    };
    setLoading(true);
    setOpState(OP_STATE.SAVING);
    setStatus("Saving project customizations...","info");
    try{
      const res=await updatePortfolioProject(selectedReport.id,projectName,payload);
      const nextPortfolio=res?.portfolio??null;
      setPortfolio(nextPortfolio);
      hydrateDrafts(nextPortfolio);
      setStatus(`Saved customization for ${projectName}.`,"success");
    }catch(e){
      setStatus(e.message??"Failed to save project customization","error");
    }finally{
      setLoading(false);
      setOpState(OP_STATE.IDLE);
    }
  }

  async function handleToggleMode(){
    if(!selectedReport?.id){setStatus("Select a report first.","error");return;}
    const current=(portfolio?.portfolio_mode??"public").toLowerCase();
    const goPrivate=current!=="private";
    setLoading(true);
    setOpState(OP_STATE.TOGGLING_MODE);
    setStatus("Updating portfolio mode...","info");
    try{
      const res=goPrivate?await unpublishPortfolio(selectedReport.id):await publishPortfolio(selectedReport.id);
      setPortfolio(res?.portfolio??portfolio);
      setStatus(goPrivate?"Private mode enabled.":"Public mode enabled.","success");
    }catch(e){
      setStatus(e.message??"Failed to change mode","error");
    }finally{
      setLoading(false);
      setOpState(OP_STATE.IDLE);
    }
  }

  const portfolioProjects=portfolio?.projects??[];
  const portfolioMode=(portfolio?.portfolio_mode??"public").toLowerCase();
  const isPrivateMode=portfolioMode==="private";
  const isPublicMode=!isPrivateMode;

  const resumeBulletCount=portfolioProjects.reduce((acc,p)=>acc+(p?.bullets?.length??0),0);
  const teamProjectCount=portfolioProjects.filter((p)=>{
    const contributors=p?.portfolio_details?.contributor_roles??[];
    return contributors.length>1||p?.collaboration_status==="collaborative";
  }).length;

  const availableLanguages=Array.from(new Set(portfolioProjects.flatMap((p)=>p?.languages??[]))).sort((a,b)=>a.localeCompare(b));

  const visiblePortfolioProjects=portfolioProjects
    .filter((p)=>{
      const d=getDraft(p.project_name);
      if(isPublicMode&&d.is_hidden)return false;
      return true;
    })
    .filter((p)=>{
      if(!isPublicMode)return true;
      const name=getRenderedTitle(p).toLowerCase();
      const matchesSearch=!searchText.trim()||name.includes(searchText.trim().toLowerCase());
      const matchesLanguage=languageFilter==="all"||(p?.languages??[]).includes(languageFilter);
      const matchesCollab=collabFilter==="all"||(p?.collaboration_status??"individual")===collabFilter;
      return matchesSearch&&matchesLanguage&&matchesCollab;
    });

  const earnedBadgesByProject=(projectName)=>(badgeProgress??[]).filter((b)=>badgeEarnedForProject(b,projectName));

  return (
    <>
      <h3>Portfolio</h3>

      <button onClick={loadInitialData} disabled={loading}>{loading?"Loading...":"Refresh Portfolio Page"}</button>

      <div className={`portfolio-status portfolio-status--${messageType}`} aria-live="polite" data-testid="portfolio-status-banner">
        {message||"Ready."}
      </div>

      <div style={{marginTop:16,padding:12,border:"1px solid #ddd",borderRadius:8}}>
        <h4>Create Portfolio Report</h4>
        <div style={{marginBottom:12}}>
          <label>Title</label><br />
          <input type="text" value={reportTitle} onChange={(e)=>setReportTitle(e.target.value)} style={{width:"100%",maxWidth:400}} />
        </div>
        <div style={{marginBottom:12}}>
          <label>Notes</label><br />
          <textarea value={reportNotes} onChange={(e)=>setReportNotes(e.target.value)} rows={4} style={{width:"100%",maxWidth:400}} />
        </div>
        <h4>Select Projects</h4>
        {projects.length===0?<p>No projects found. Upload a project first.</p>:(
          <ul style={{listStyle:"none",paddingLeft:0}}>
            {projects.map((p)=>(
              <li key={p.id} style={{marginBottom:8}}>
                <label>
                  <input type="checkbox" checked={selectedProjectIds.includes(p.id)} onChange={()=>toggleProject(p.id)} style={{marginRight:8}} />
                  {p.name} (#{p.id})
                </label>
              </li>
            ))}
          </ul>
        )}
        <button onClick={handleCreateReport} disabled={loading}>{loading?"Working...":"Create Portfolio Report"}</button>
      </div>

      <div style={{display:"flex",gap:16,marginTop:16}}>
        <div style={{minWidth:300}}>
          <h4>Saved Reports</h4>
          {reports.length===0?<p>No reports created yet.</p>:(
            <ul>
              {reports.map((r)=>(
                <li key={r.id}>
                  <button
                    onClick={() => handleSelectReport(r.id)}
                    disabled={loading}
                    style={{ background: "transparent", border: "none", cursor: "pointer", padding: 0, color: "var(--text)" }}
                  >
                    {r.title ?? `Report #${r.id}`}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div style={{flex:1}}>
          <h4>Selected Report</h4>
          {!selectedReport?<p>Select a report to view details.</p>:(
            <div className="portfolio-selected-report-card" data-testid="selected-report-card">
              <p><strong>Title:</strong> {selectedReport.title??`Report #${selectedReport.id}`}</p>
              <p><strong>ID:</strong> {selectedReport.id}</p>
              <p><strong>Kind:</strong> {selectedReport.report_kind??"portfolio"}</p>
              <p><strong>Sort:</strong> {selectedReport.sort_by??"resume_score"}</p>
              <p><strong>Projects:</strong> {selectedReport.project_count??"Unknown"}</p>
              {selectedReport.date_created?<p><strong>Created:</strong> {new Date(selectedReport.date_created).toLocaleString()}</p>:null}
            </div>
          )}
        </div>
      </div>

      <div style={{marginTop:12}}>
        <button onClick={handleExportPortfolioPdf} disabled={loading||!selectedReport?.id}>
          {opState===OP_STATE.EXPORTING?"Exporting PDF...":"Export Portfolio PDF"}
        </button>
        <button onClick={handleGenerateWebPortfolio} disabled={loading||!selectedReport?.id} style={{marginLeft:8}}>
          {opState===OP_STATE.GENERATING?"Generating...":"Generate Web Portfolio"}
        </button>
        <button onClick={handleCopyPortfolioHtml} disabled={loading||!portfolio} style={{marginLeft:8}}>
          Copy Portfolio HTML
        </button>
      </div>

      {portfolio?(
        <section className="portfolio-panel">
          <div className="portfolio-summary-strip">
            <div className="summary-pill"><span className="summary-label">Projects</span><strong>{portfolioProjects.length}</strong></div>
            <div className="summary-pill"><span className="summary-label">Resume bullets</span><strong>{resumeBulletCount}</strong></div>
            <div className="summary-pill"><span className="summary-label">Team projects</span><strong>{teamProjectCount}</strong></div>
          </div>

          <h4>{portfolio.title||"Portfolio"}</h4>

          <div style={{marginBottom:12,display:"flex",alignItems:"center",gap:8}}>
            <strong>Mode:</strong>
            <span data-testid="portfolio-mode-badge">{isPrivateMode?"private":"public"}</span>
            <button
              onClick={handleToggleMode}
              disabled={loading||!selectedReport?.id}
              aria-label="Toggle portfolio mode"
              title={isPrivateMode?"Switch to public mode":"Switch to private mode"}
              style={{padding:"6px 10px",fontSize:"1rem"}}
            >
              {isPrivateMode?"🔒":"🔓"}
            </button>
          </div>

          {isPublicMode?(
            <div style={{marginBottom:16,display:"flex",gap:8,flexWrap:"wrap"}}>
              <input aria-label="Search projects" placeholder="Search projects..." value={searchText} onChange={(e)=>setSearchText(e.target.value)} />
              <select aria-label="Filter by language" value={languageFilter} onChange={(e)=>setLanguageFilter(e.target.value)}>
                <option value="all">All languages</option>
                {availableLanguages.map((lang)=><option key={lang} value={lang}>{lang}</option>)}
              </select>
              <select aria-label="Filter by collaboration" value={collabFilter} onChange={(e)=>setCollabFilter(e.target.value)}>
                <option value="all">All collaboration</option>
                <option value="individual">Individual</option>
                <option value="collaborative">Collaborative</option>
              </select>
            </div>
          ):null}

          <div style={{display:"flex",flexDirection:"column",gap:12}}>
            {visiblePortfolioProjects.map((project,idx)=>{
              const details=project?.portfolio_details??{};
              const key=`${project?.project_name??"project"}-${idx}`;
              const isOpen=!!openProjects[key];
              const contributorRoles=details?.contributor_roles??[];
              const renderedTitle=getRenderedTitle(project);
              const renderedOverview=getRenderedOverview(project);
              const renderedAchievements=getRenderedAchievements(project);
              const draft=getDraft(project.project_name);
              const projectBadges=earnedBadgesByProject(project.project_name);

              return (
                <article className="portfolio-card" key={key}>
                  <button onClick={()=>togglePortfolioProject(key)} style={{width:"100%",display:"flex",justifyContent:"space-between",background:"transparent",border:"none",color:"inherit",cursor:"pointer",padding:0}}>
                    <span style={{display:"flex",alignItems:"center",gap:8,flexWrap:"wrap"}}>
                      {isPrivateMode?(
                        <input
                          aria-label={`Custom title ${project?.project_name??""}`}
                          type="text"
                          value={draft.custom_title}
                          onClick={(e)=>e.stopPropagation()}
                          onChange={(e)=>handleDraftChange(project.project_name,"custom_title",e.target.value)}
                          placeholder={project?.project_name??"Untitled Project"}
                          style={{fontWeight:700,background:"transparent",border:"1px solid #3d6d92",color:"inherit",padding:"2px 6px",borderRadius:6,minWidth:240}}
                        />
                      ):(
                        <strong>{renderedTitle}</strong>
                      )}

                      {projectBadges.map((b)=>(
                        <span key={`proj-badge-title-${project.project_name}-${b.badge_id}`} className="portfolio-badge-chip portfolio-badge-chip--unlocked" onClick={(e)=>e.stopPropagation()}>
                          🏅 {b.label??formatBadgeLabel(b.badge_id)}
                        </span>
                      ))}
                    </span>
                    <span>{isOpen?"▾ Collapse":"▸ Expand"}</span>
                  </button>

                  {isOpen?(
                    <div style={{marginTop:10}}>
                      <p className="portfolio-meta"><strong>{details?.role||"Contributor"}</strong> • {details?.timeline||"Timeline unavailable"}</p>

                      {isPrivateMode?(
                        <>
                          <label>Portfolio entry</label>
                          <textarea
                            aria-label={`Custom overview ${project?.project_name??""}`}
                            rows={5}
                            value={draft.custom_overview}
                            onChange={(e)=>handleDraftChange(project.project_name,"custom_overview",e.target.value)}
                            style={{width:"100%",marginTop:6}}
                          />
                        </>
                      ):(
                        <p className="portfolio-overview">{renderedOverview}</p>
                      )}

                      {isPrivateMode?(
                        <>
                          <label>Key contributions (one per line)</label>
                          <textarea
                            aria-label={`Custom achievements ${project?.project_name??""}`}
                            rows={5}
                            value={draft.custom_achievements}
                            onChange={(e)=>handleDraftChange(project.project_name,"custom_achievements",e.target.value)}
                            style={{width:"100%",marginTop:6}}
                          />
                        </>
                      ):(
                        renderedAchievements.length?(<><strong>Key contributions</strong><ul>{renderedAchievements.map((b,i)=><li key={`b-${i}`}>{b}</li>)}</ul></>):null
                      )}

                      {contributorRoles.length?(<><strong>Contributors</strong><ul className="contrib-list">{contributorRoles.map((c,i)=><li key={`cr-${i}`}><span>{c.name}</span>{c.role?<span className="confidence-chip">{c.role}</span>:null}</li>)}</ul></>):null}

                      {isPrivateMode?(
                        <div style={{marginTop:10}}>
                          <label>
                            <input
                              type="checkbox"
                              checked={!!draft.is_hidden}
                              onChange={(e)=>handleDraftChange(project.project_name,"is_hidden",e.target.checked)}
                              style={{marginRight:6}}
                            />
                            Hide in public mode
                          </label>
                          <div>
                            <button onClick={()=>handleSaveProjectCustomization(project.project_name)} disabled={loading} style={{marginTop:8}}>
                              {opState===OP_STATE.SAVING?"Saving...":"Save Changes"}
                            </button>
                          </div>
                        </div>
                      ):null}
                    </div>
                  ):null}
                </article>
              );
            })}
          </div>
        </section>
      ):null}

      {copyToastVisible?(
        <div
          role="status"
          aria-live="polite"
          style={{
            position:"fixed",
            right:16,
            bottom:16,
            zIndex:9999,
            background:"#1f8f43",
            color:"#fff",
            border:"1px solid #157535",
            boxShadow:"0 8px 24px rgba(0,0,0,.24)",
            borderRadius:10,
            padding:"10px 14px",
            display:"flex",
            alignItems:"center",
            gap:8,
            fontWeight:600,
          }}
          data-testid="copy-html-toast"
        >
          <span aria-hidden="true">✅</span>
          <span>Successfully copied!</span>
        </div>
      ):null}
    </>
  );
}

export default PortfolioPage;