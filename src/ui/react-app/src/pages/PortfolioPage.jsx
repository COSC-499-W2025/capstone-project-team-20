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
} from "../api/client";

function PortfolioPage() {
  const [loading,setLoading]=useState(false);
  const [message,setMessage]=useState("");
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

  useEffect(()=>{loadInitialData();},[]);

  async function loadInitialData(){
    setLoading(true);
    setMessage("");
    try{
      const [projectData,reportData]=await Promise.all([listProjects(),listReports()]);
      const allProjects=projectData.projects??[];
      setProjects(allProjects);

      setSelectedProjectIds(allProjects.map((p) => p.id));
      const filteredReports = (reportData.reports ?? []).filter((r) => (r.report_kind ?? "resume") === "portfolio");
      setReports(filteredReports);

      if (selectedReport?.id) {
        const refreshed = filteredReports.find((r) => r.id === selectedReport.id);
        setSelectedReport(refreshed ?? selectedReport);
      }
    }catch(e){
      setMessage(e.message??"Failed to load portfolio page data");
    }finally{
      setLoading(false);
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

  async function handleCreateReport(){
    setLoading(true);
    setMessage("");
    try{
      await setPrivacyConsent(true);

      if (!selectedProjectIds.length) {
        setMessage("Select at least one project first.");
        return;
      }

      const created = await createReport({
        title: reportTitle,
        sort_by: "resume_score",
        notes: reportNotes,
        report_kind: "portfolio",
        project_ids: selectedProjectIds,

      });
      setSelectedReport(created.report??null);
      setMessage(`Created report "${created.report?.title??"Untitled"}"`);
      await loadInitialData();
    }catch(e){
      setMessage(e.message??"Failed to create report");
    }finally{
      setLoading(false);
    }
  }

  async function handleSelectReport(id){
    setLoading(true);
    setMessage("");
    setPortfolio(null);
    setOpenProjects({});
    setProjectDrafts({});
    try{
      const data=await getReport(id);
      setSelectedReport(data.report??null);
    }catch(e){
      setMessage(e.message??"Failed to load report");
    }finally{
      setLoading(false);
    }
  }

  async function handleExportPortfolioPdf(){
    if(!selectedReport?.id){setMessage("Select or create a report first.");return;}
    setLoading(true);
    setMessage("");
    try{
      const exp=await exportPortfolio({report_id:selectedReport.id,output_name:"portfolio.pdf"});
      const fileName=`${selectedReport.title??`report-${selectedReport.id}`}.pdf`;
      const res=await fetch(`http://localhost:8000${exp.download_url}`);
      const blob=await res.blob();
      const objectUrl=URL.createObjectURL(blob);
      const a=document.createElement("a");
      a.href=objectUrl;
      a.download=fileName;
      a.click();
      URL.revokeObjectURL(objectUrl);
      setMessage("Portfolio export started.");
    }catch(e){
      setMessage(e.message??"Failed to export portfolio");
    }finally{
      setLoading(false);
    }
  }

  async function handleGenerateWebPortfolio(){
    if(!selectedReport?.id){setMessage("Select or create a report first.");return;}
    setLoading(true);
    setMessage("");
    setPortfolio(null);
    setOpenProjects({});
    setProjectDrafts({});
    try{
      await setPrivacyConsent(true);
      const names=projects.filter((p)=>selectedProjectIds.includes(p.id)).map((p)=>p.name).filter(Boolean);
      if(!names.length){setMessage("Select at least one project first.");return;}
      await generatePortfolioDetailsForReport({report_id:selectedReport.id,project_names:names});
      const response=await getPortfolio(selectedReport.id);
      const nextPortfolio=response?.portfolio??null;
      setPortfolio(nextPortfolio);
      hydrateDrafts(nextPortfolio);

      const initialOpen={};
      (nextPortfolio?.projects??[]).forEach((p,idx)=>{initialOpen[`${p?.project_name??"project"}-${idx}`]=idx===0;});
      setOpenProjects(initialOpen);
      setMessage("Web portfolio generated.");
    }catch(e){
      setMessage(e.message??"Failed to generate web portfolio");
    }finally{
      setLoading(false);
    }
  }

  async function handleSaveProjectCustomization(projectName){
    if(!selectedReport?.id){setMessage("Select a report first.");return;}
    const draft=getDraft(projectName);
    const payload={
      custom_title:(draft.custom_title??"").trim(),
      custom_overview:(draft.custom_overview??"").trim(),
      custom_achievements:(draft.custom_achievements??"").split("\n").map((x)=>x.trim()).filter(Boolean),
      is_hidden:!!draft.is_hidden,
    };
    setLoading(true);
    setMessage("");
    try{
      const res=await updatePortfolioProject(selectedReport.id,projectName,payload);
      const nextPortfolio=res?.portfolio??null;
      setPortfolio(nextPortfolio);
      hydrateDrafts(nextPortfolio);
      setMessage(`Saved customization for ${projectName}.`);
    }catch(e){
      setMessage(e.message??"Failed to save project customization");
    }finally{
      setLoading(false);
    }
  }

  async function handleToggleMode(){
    if(!selectedReport?.id){setMessage("Select a report first.");return;}
    const current=(portfolio?.portfolio_mode??"public").toLowerCase();
    const goPrivate=current!=="private";
    setLoading(true);
    setMessage("");
    try{
      const res=goPrivate
        ? await unpublishPortfolio(selectedReport.id)
        : await publishPortfolio(selectedReport.id);
      setPortfolio(res?.portfolio??portfolio);
      setMessage(goPrivate?"Private mode enabled.":"Public mode enabled.");
    }catch(e){
      setMessage(e.message??"Failed to change mode");
    }finally{
      setLoading(false);
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

  return (
    <>
      <h3>Portfolio</h3>

      <button onClick={loadInitialData} disabled={loading}>{loading?"Loading...":"Refresh Portfolio Page"}</button>

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
          {selectedReport?<pre>{JSON.stringify(selectedReport,null,2)}</pre>:<p>Select a report to view details.</p>}
        </div>
      </div>

      <div style={{marginTop:12}}>
        <button onClick={handleExportPortfolioPdf} disabled={loading||!selectedReport?.id}>Export Portfolio PDF</button>
        <button onClick={handleGenerateWebPortfolio} disabled={loading||!selectedReport?.id} style={{marginLeft:8}}>
          {loading?"Working...":"Generate Web Portfolio"}
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

              return (
                <article className="portfolio-card" key={key}>
                  <button onClick={()=>togglePortfolioProject(key)} style={{width:"100%",display:"flex",justifyContent:"space-between",background:"transparent",border:"none",color:"inherit",cursor:"pointer",padding:0}}>
                    <span>
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

                      {contributorRoles.length?(<><strong>Contributors</strong><ul className="contrib-list">{contributorRoles.map((c,i)=><li key={`cr-${i}`}><span>{c.name}</span><span className="confidence-chip">{c.role}</span></li>)}</ul></>):null}

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
                              Save Changes
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

      {message&&<p style={{marginTop:12}}>{message}</p>}
    </>
  );
}

export default PortfolioPage;
