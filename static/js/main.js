function switchAuthTab(t){
  document.querySelectorAll('.auth-tab').forEach((el,i)=>el.classList.toggle('active',['login','signup'][i]===t));
  document.getElementById('loginForm').style.display=t==='login'?'block':'none';
  document.getElementById('signupForm').style.display=t==='signup'?'block':'none';
}

async function submitLogin(){
  const u=document.getElementById('authLoginUser').value.trim();
  const p=document.getElementById('authLoginPass').value.trim();
  const msg=document.getElementById('loginMsg');
  msg.textContent='';msg.className='auth-msg';
  if(!u||!p){msg.className='auth-msg err';msg.textContent='Fill both fields.';return;}
  try{
    const res=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})});
    const data=await res.json();
    if(data.success){
      if(data.is_admin){ window.location.href='/admin'; return; }
      const banner=document.getElementById('welcomeBanner');
      if(data.login_count>1){
        banner.textContent=`👋 Welcome back, ${u}! You've logged in ${data.login_count} times.`;
        banner.style.display='block';
        setTimeout(()=>{banner.style.display='none';enterApp(u);},1800);
      } else { enterApp(u); }
    } else { msg.className='auth-msg err'; msg.textContent='❌ Invalid username or password.'; }
  }catch(e){msg.className='auth-msg err';msg.textContent='Error: '+e.message;}
}

// ── Wallet login ───────────────────────────────────────────────────────────
let pendingWalletAddress = null;

async function connectWallet(){
  const msg = document.getElementById('walletMsg') || document.getElementById('walletMsg2');
  const setMsg = (m, err=false) => {
    ['walletMsg','walletMsg2'].forEach(id=>{
      const el=document.getElementById(id);
      if(el){el.textContent=m;el.className='auth-msg '+(err?'err':'ok');}
    });
  };
  if(!window.ethereum){
    setMsg('❌ MetaMask not found. Install it from metamask.io', true);
    return;
  }
  try{
    // Request account
    const accounts = await window.ethereum.request({method:'eth_requestAccounts'});
    const address = accounts[0].toLowerCase();

    // Check network — must be Sepolia (chainId 0xaa36a7 = 11155111)
    const chainId = await window.ethereum.request({method:'eth_chainId'});
    if(chainId !== '0xaa36a7'){
      setMsg('❌ Please switch to Sepolia Testnet in MetaMask', true);
      try{
        await window.ethereum.request({
          method:'wallet_switchEthereumChain',
          params:[{chainId:'0xaa36a7'}]
        });
      }catch(e){ return; }
    }

    setMsg('⏳ Requesting signature...');

    // Get challenge from server
    const chalRes = await fetch('/wallet/challenge',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({address})
    });
    const chalData = await chalRes.json();
    if(!chalData.success){setMsg('❌ '+chalData.message, true);return;}

    // Ask MetaMask to sign
    const signature = await window.ethereum.request({
      method:'personal_sign',
      params:[chalData.challenge, accounts[0]]
    });

    setMsg('⏳ Verifying signature...');

    // Verify on server
    const verRes = await fetch('/wallet/verify',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({address, signature})
    });
    const verData = await verRes.json();
    if(!verData.success){setMsg('❌ '+verData.message, true);return;}

    if(verData.exists){
      // Returning wallet user
      const banner=document.getElementById('welcomeBanner');
      if(verData.login_count>1){
        banner.textContent='👋 Welcome back, '+verData.username+'! Connected via MetaMask.';
        banner.style.display='block';
        setTimeout(()=>{banner.style.display='none';enterApp(verData.username);},1800);
      } else { enterApp(verData.username); }
    } else {
      // New wallet user — show username setup
      pendingWalletAddress = address;
      document.getElementById('loginForm').style.display='none';
      document.getElementById('signupForm').style.display='none';
      document.getElementById('walletSetupForm').style.display='block';
      document.getElementById('connectedAddress').textContent='🦊 Connected: '+address.substring(0,6)+'...'+address.substring(38);
      setMsg('');
    }
  }catch(e){
    if(e.code===4001){setMsg('❌ Signature rejected by user.', true);}
    else{setMsg('❌ '+e.message, true);}
  }
}

async function submitWalletUsername(){
  const displayName = document.getElementById('walletDisplayName').value.trim();
  const msg = document.getElementById('walletSetupMsg');
  msg.textContent=''; msg.className='auth-msg';
  if(!displayName){msg.className='auth-msg err';msg.textContent='Enter a display name.';return;}
  if(!pendingWalletAddress){msg.className='auth-msg err';msg.textContent='Wallet not connected. Start again.';return;}
  try{
    const res = await fetch('/wallet/register',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({address: pendingWalletAddress, display_name: displayName})
    });
    const data = await res.json();
    if(data.success){
      enterApp(data.username);
    } else {
      msg.className='auth-msg err';
      msg.textContent='❌ '+data.message;
    }
  }catch(e){msg.className='auth-msg err';msg.textContent='Error: '+e.message;}
}

async function submitSignup(){
  const u=document.getElementById('authSignupUser').value.trim();
  const p=document.getElementById('authSignupPass').value.trim();
  const c=document.getElementById('authSignupPassConfirm').value.trim();
  const msg=document.getElementById('signupMsg');
  msg.textContent='';msg.className='auth-msg';
  if(!u||!p){msg.className='auth-msg err';msg.textContent='Fill all fields.';return;}
  if(p!==c){msg.className='auth-msg err';msg.textContent='❌ Passwords do not match.';return;}
  if(p.length<4){msg.className='auth-msg err';msg.textContent='❌ Password too short (min 4).';return;}
  try{
    const res=await fetch('/signup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})});
    const data=await res.json();
    if(data.success){msg.className='auth-msg ok';msg.textContent='✅ Account created! Logging in...';setTimeout(()=>enterApp(u),900);}
    else{msg.className='auth-msg err';msg.textContent='❌ '+data.message;}
  }catch(e){msg.className='auth-msg err';msg.textContent='Error: '+e.message;}
}

function enterApp(username){
  document.getElementById('authPage').style.display='none';
  document.getElementById('appShell').style.display='block';
  document.getElementById('loggedInUsername').textContent=username;
  checkPinataStatus();
}

async function doLogout(){
  await fetch('/logout',{method:'POST'});
  document.getElementById('appShell').style.display='none';
  document.getElementById('authPage').style.display='flex';
  document.getElementById('authLoginPass').value='';
  document.getElementById('authLoginUser').value='';
  document.getElementById('loginMsg').textContent='';
  // reset to register tab
  switchTab('register');
}

function switchTab(name){
  const names=['register','verify','retrieve','chain'];
  document.querySelectorAll('.tab').forEach((t,i)=>t.classList.toggle('active',names[i]===name));
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.getElementById('panel-'+name).classList.add('active');
  if(name==='chain')loadChain();
  if(name==='retrieve')loadMyFiles();
}

['registerZone','verifyZone'].forEach(id=>{
  const z=document.getElementById(id);
  z.addEventListener('dragover',e=>{e.preventDefault();z.classList.add('drag');});
  z.addEventListener('dragleave',()=>z.classList.remove('drag'));
  z.addEventListener('drop',e=>{e.preventDefault();z.classList.remove('drag');const f=e.dataTransfer.files[0];if(!f)return;id==='registerZone'?handleRegisterFile(f):handleVerifyFile(f);});
});

async function handleRegisterFile(file){
  if(!file)return;
  const bar=document.getElementById('registerMining'),status=document.getElementById('registerStatus');
  bar.classList.add('active');
  status.innerHTML=`<p style="font-family:var(--mono);font-size:.8rem;color:var(--muted);margin-top:12px">⛏ Mining block for <strong>${file.name}</strong>...</p>`;
  const fd=new FormData();fd.append('file',file);
  try{
    const res=await fetch('/register',{method:'POST',body:fd});
    const data=await res.json();
    bar.classList.remove('active');
    if(data.status==='registered'){status.innerHTML=`<div class="result-card success"><div class="result-title">✅ Registered Successfully</div><div class="result-meta">FILE &nbsp;&nbsp;&nbsp;&nbsp;<span class="hash-val">${data.file_name}</span><br/>TYPE &nbsp;&nbsp;&nbsp;&nbsp;<span class="hash-val">${data.file_type}</span><br/>HASH &nbsp;&nbsp;&nbsp;&nbsp;<span class="hash-val">${data.file_hash}</span><br/>BLOCK &nbsp;&nbsp;&nbsp;<span class="hash-val">#${data.block_index}</span><br/>NONCE &nbsp;&nbsp;&nbsp;<span class="hash-val">${data.nonce}</span><br/>IPFS CID <span class="hash-val">${data.ipfs_cid}</span></div></div>`;}
    else if(data.status==='exists'){status.innerHTML=`<div class="result-card info"><div class="result-title">ℹ️ Already Registered</div><div class="result-meta">FILE &nbsp;&nbsp;&nbsp;&nbsp;<span class="hash-val">${data.file_name}</span><br/>BLOCK &nbsp;&nbsp;&nbsp;<span class="hash-val">#${data.block_index}</span><br/>HASH &nbsp;&nbsp;&nbsp;&nbsp;<span class="hash-val">${data.file_hash}</span></div></div>`;}
    else{status.innerHTML=`<div class="result-card danger"><div class="result-title">❌ Error</div><div class="result-meta">${data.message}</div></div>`;}
  }catch(e){bar.classList.remove('active');status.innerHTML=`<div class="result-card danger"><div class="result-title">❌ Failed</div><div class="result-meta">${e.message}</div></div>`;}
}

async function handleVerifyFile(file){
  if(!file)return;
  const bar=document.getElementById('verifyMining'),status=document.getElementById('verifyStatus');
  bar.classList.add('active');
  status.innerHTML=`<p style="font-family:var(--mono);font-size:.8rem;color:var(--muted);margin-top:12px">🔍 Verifying <strong>${file.name}</strong>...</p>`;
  const fd=new FormData();fd.append('file',file);
  try{
    const res=await fetch('/verify',{method:'POST',body:fd});
    const data=await res.json();
    bar.classList.remove('active');
    if(data.verified){status.innerHTML=`<div class="result-card success"><div class="result-title">✅ Integrity Verified</div><div class="result-meta">FILE &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="hash-val">${data.file_name}</span><br/>TYPE &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="hash-val">${data.file_type}</span><br/>HASH &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="hash-val">${data.file_hash}</span><br/>REG BLOCK &nbsp;<span class="hash-val">#${data.block_index}</span><br/>CHAIN OK &nbsp;&nbsp;<span class="hash-val">${data.chain_valid?'✅ Valid':'❌ Tampered'}</span></div></div>`;}
    else{status.innerHTML=`<div class="result-card danger"><div class="result-title">❌ ${data.reason==='not_found'?'File Not Registered':'Tampered / Unknown'}</div><div class="result-meta">FILE &nbsp;&nbsp;<span class="hash-val">${data.file_name}</span><br/>HASH &nbsp;&nbsp;<span class="hash-val">${data.file_hash}</span><br/>${data.reason==='not_found'?'No record in the blockchain.':'Hash mismatch detected.'}</div></div>`;}
  }catch(e){bar.classList.remove('active');status.innerHTML=`<div class="result-card danger"><div class="result-title">❌ Failed</div><div class="result-meta">${e.message}</div></div>`;}
}

function fileIcon(t){return{image:'🖼️',document:'📄',ml_model:'🤖',file:'📁'}[t]||'📁';}

async function loadMyFiles(){
  const list=document.getElementById('fileList');
  list.innerHTML='<div class="empty-state"><div class="empty-icon">⏳</div><p>Loading your files...</p></div>';
  try{
    const res=await fetch('/my_files');
    if(res.status===401){doLogout();return;}
    const data=await res.json();
    const files=data.files;
    if(!files||files.length===0){list.innerHTML='<div class="empty-state"><div class="empty-icon">📭</div><p>No files yet.<br/>Go to Register tab to add files.</p></div>';return;}
    list.innerHTML=files.map(f=>`
      <div class="file-card">
        <div class="file-preview">
          ${f.preview?`<img src="${f.preview}" alt="${f.file_name}"/>`:`<div class="file-icon-big">${fileIcon(f.file_type)}</div>`}
          <div class="ftype-badge">${f.file_type.toUpperCase()}</div>
        </div>
        <div class="file-info">
          <div class="file-name" title="${f.file_name}">${f.file_name}</div>
          <div class="file-detail">BLOCK &nbsp;&nbsp;#${f.index}<br/>HASH &nbsp;&nbsp;&nbsp;<span class="file-hash-short">${f.file_hash.substring(0,16)}...</span><br/>DATE &nbsp;&nbsp;&nbsp;${new Date(f.timestamp*1000).toLocaleDateString()}<br/>NONCE &nbsp;&nbsp;${f.nonce}</div>
          <div class="file-actions">
            <button class="btn-dl" onclick="downloadFile('${f.file_hash}','${f.file_name}')">⬇ Download</button>
            <button class="btn btn-outline btn-sm" onclick="copyHash('${f.file_hash}')">📋</button>
            <button class="btn-danger-sm" onclick="deleteFile('${f.file_hash}','${f.file_name}')">🗑</button>
          </div>
        </div>
      </div>`).join('');
  }catch(e){list.innerHTML=`<div class="empty-state"><div class="empty-icon">❌</div><p>${e.message}</p></div>`;}
}

function copyHash(h){navigator.clipboard.writeText(h);alert('Hash copied!');}

async function downloadFile(fileHash, fileName){
  try{
    const res=await fetch(`/download/${fileHash}`);
    if(!res.ok){alert('File not found on server. It may have been deleted.');return;}
    const blob=await res.blob();
    const url=URL.createObjectURL(blob);
    const a=document.createElement('a');
    a.href=url;a.download=fileName;a.click();
    URL.revokeObjectURL(url);
  }catch(e){alert('Download failed: '+e.message);}
}

async function deleteFile(fileHash,fileName){
  if(!confirm(`Remove "${fileName}" from your files?\n\nThe blockchain record stays intact.`))return;
  try{
    const res=await fetch('/delete_file',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({file_hash:fileHash})});
    const data=await res.json();
    if(data.success)loadMyFiles();
    else alert('Error: '+data.message);
  }catch(e){alert('Failed: '+e.message);}
}

async function loadChain(){
  const list=document.getElementById('chainList');
  list.innerHTML='<p style="color:var(--muted);font-family:var(--mono);font-size:.8rem">Loading...</p>';
  try{
    const res=await fetch('/chain');const data=await res.json();
    document.getElementById('statBlocks').textContent=data.chain.length;
    document.getElementById('statCID').textContent=data.cid||'Not synced';
    document.getElementById('validityBanner').innerHTML=`<div class="validity-banner ${data.valid?'valid':'invalid'}">${data.valid?'🔒 Blockchain valid — all blocks intact':'⚠️ Chain integrity compromised!'}</div>`;
    list.innerHTML=data.chain.map((b,i)=>`${i>0?'<div class="chain-link">↓</div>':''}<div class="chain-block"><div class="block-index">${b.index}</div><div><div class="block-name">${b.file_name}</div><div class="block-meta">${new Date(b.timestamp*1000).toLocaleString()} | nonce: ${b.nonce} | ${b.file_type}</div><div class="block-meta" style="margin-top:3px;color:#475569">${b.current_hash.substring(0,32)}...</div></div><div class="block-badge">${b.file_type.toUpperCase()}</div></div>`).join('');
  }catch(e){list.innerHTML=`<p style="color:var(--warn);font-family:var(--mono);font-size:.8rem">Error: ${e.message}</p>`;}
}

async function checkPinataStatus(){
  try{const res=await fetch('/pinata_status');const data=await res.json();document.getElementById('pinataStatus').className='status-pill '+(data.connected?'ok':'fail');document.getElementById('pinataStatusText').textContent=data.connected?'Pinata Connected':'Pinata Offline';}catch{}
}

(async()=>{
  try{const res=await fetch('/auth_status');const data=await res.json();if(data.logged_in)enterApp(data.username);}catch{}
})();