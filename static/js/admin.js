async function submitAdminLogin(){
  const pass=document.getElementById('adminPassInput').value.trim();
  const msg=document.getElementById('adminLoginMsg');
  msg.textContent='';
  if(!pass){msg.textContent='Enter password.';return;}
  try{
    const res=await fetch('/admin/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pass})});
    const data=await res.json();
    if(data.success){enterAdminPanel();}
    else{msg.textContent='❌ Wrong admin password.';}
  }catch(e){msg.textContent='Error: '+e.message;}
}

function enterAdminPanel(){
  document.getElementById('adminAuthPage').style.display='none';
  document.getElementById('adminShell').style.display='block';
  loadAdminDashboard();
  checkAdminPinata();
}

async function adminLogout(){
  await fetch('/admin/logout',{method:'POST'});
  document.getElementById('adminShell').style.display='none';
  document.getElementById('adminAuthPage').style.display='flex';
  document.getElementById('adminPassInput').value='';
}

function switchAdminTab(name){
  const names=['dashboard','users','config'];
  document.querySelectorAll('.tab').forEach((t,i)=>t.classList.toggle('active',names[i]===name));
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.getElementById('apanel-'+name).classList.add('active');
  if(name==='users')loadAdminUsers();
  if(name==='dashboard')loadAdminDashboard();
}

async function loadAdminDashboard(){
  try{
    const [uRes,cRes]=await Promise.all([fetch('/admin/users'),fetch('/chain')]);
    const uData=await uRes.json();
    const cData=await cRes.json();
    const users=uData.users||[];
    const totalFiles=users.reduce((s,u)=>s+u.file_count,0);
    document.getElementById('aStat-users').textContent=users.length;
    document.getElementById('aStat-files').textContent=totalFiles;
    document.getElementById('aStat-blocks').textContent=cData.chain?cData.chain.length:'—';
    document.getElementById('aStat-valid').textContent=cData.valid?'✅':'❌';
    document.getElementById('aStat-cid').textContent=cData.cid||'Not synced';
  }catch(e){console.error(e);}
}

async function loadAdminUsers(){
  const tbody=document.getElementById('usersBody');
  tbody.innerHTML='<tr><td colspan="6" style="color:var(--muted);text-align:center;padding:24px">Loading...</td></tr>';
  try{
    const res=await fetch('/admin/users');
    const data=await res.json();
    const users=data.users||[];
    if(users.length===0){tbody.innerHTML='<tr><td colspan="6" style="color:var(--muted);text-align:center;padding:24px">No users yet.</td></tr>';return;}
    tbody.innerHTML=users.map(u=>`
      <tr>
        <td><span class="user-name">👤 ${u.username}</span></td>
        <td><span class="file-count">${u.file_count} files</span></td>
        <td>${new Date(u.created_at*1000).toLocaleDateString()}</td>
        <td>${u.last_login?new Date(u.last_login*1000).toLocaleDateString():'Never'}</td>
        <td>${u.login_count||0}</td>
        <td><button class="btn-outline btn-sm" onclick="toggleUserFiles('${u.username}')">View Files</button>
            <button class="btn-danger btn-sm" style="margin-left:6px" onclick="deleteUser('${u.username}')">Delete</button></td>
      </tr>
      <tr id="ufiles-${u.username}" style="display:none">
        <td colspan="6">
          <div class="user-files">
            ${u.files.length===0
              ?'<div style="color:var(--muted);font-family:var(--mono);font-size:.72rem;padding:8px">No files registered.</div>'
              :u.files.map(f=>`<div class="user-file-item"><span>${{image:'🖼️',document:'📄',ml_model:'🤖',file:'📁'}[f.type]||'📁'}</span><span class="ufi-name">${f.name}</span><span class="ufi-hash">${f.hash.substring(0,20)}...</span><span>${new Date(f.added*1000).toLocaleDateString()}</span></div>`).join('')
            }
          </div>
        </td>
      </tr>
    `).join('');
  }catch(e){tbody.innerHTML=`<tr><td colspan="6" style="color:var(--warn);text-align:center;padding:24px">${e.message}</td></tr>`;}
}

function toggleUserFiles(username){
  const row=document.getElementById('ufiles-'+username);
  row.style.display=row.style.display==='none'?'table-row':'none';
}

async function deleteUser(username){
  if(!confirm(`Delete user "${username}" and all their file records?\n\nBlockchain blocks will remain.`))return;
  try{
    const res=await fetch('/admin/delete_user',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username})});
    const data=await res.json();
    if(data.success)loadAdminUsers();
    else alert('Error: '+data.message);
  }catch(e){alert('Failed: '+e.message);}
}

async function saveAdminConfig(){
  const key=document.getElementById('aCfgApiKey').value.trim();
  const secret=document.getElementById('aCfgSecretKey').value.trim();
  const diff=document.getElementById('aCfgDifficulty').value;
  const result=document.getElementById('aCfgResult');
  result.textContent='Testing...'; result.className='result-msg';
  try{
    const res=await fetch('/admin/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_key:key,secret_key:secret,difficulty:parseInt(diff)})});
    const data=await res.json();
    result.className='result-msg '+(data.success?'ok':'err');
    result.textContent=data.message;
    if(data.success)checkAdminPinata();
  }catch(e){result.className='result-msg err';result.textContent='Failed: '+e.message;}
}

async function changeAdminPass(){
  const oldP=document.getElementById('aOldPass').value.trim();
  const newP=document.getElementById('aNewPass').value.trim();
  const result=document.getElementById('aPassResult');
  result.textContent=''; result.className='result-msg';
  if(!oldP||!newP){result.className='result-msg err';result.textContent='Fill both fields.';return;}
  try{
    const res=await fetch('/admin/change_password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({old_password:oldP,new_password:newP})});
    const data=await res.json();
    result.className='result-msg '+(data.success?'ok':'err');
    result.textContent=data.message;
  }catch(e){result.className='result-msg err';result.textContent='Failed: '+e.message;}
}

async function checkAdminPinata(){
  try{
    const res=await fetch('/pinata_status');const data=await res.json();
    document.getElementById('adminPinataStatus').className='status-pill '+(data.connected?'ok':'fail');
    document.getElementById('adminPinataText').textContent=data.connected?'Pinata Connected':'Pinata Offline';
  }catch{}
}

(async()=>{
  try{const res=await fetch('/admin/auth_status');const data=await res.json();if(data.logged_in)enterAdminPanel();}catch{}
})();

// Also check main session admin flag
(async()=>{
  try{
    const res=await fetch('/admin/auth_status');
    const data=await res.json();
    if(data.logged_in){ enterAdminPanel(); }
  }catch{}
})();