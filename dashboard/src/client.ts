export interface User { id:string; email:string; tenant:string; role:'admin'|'analyst'|'viewer' }
export async function api<T>(path:string, method='GET', body?:unknown):Promise<T> {
  const response=await fetch('/api'+path,{method,credentials:'same-origin',headers:{'Content-Type':'application/json','X-Requested-With':'secure-ai'},body:body===undefined?undefined:JSON.stringify(body)});
  const data=await response.json();
  if(!response.ok) throw new Error(typeof data.detail==='string'?data.detail:'The request could not be completed. Check the input.');
  return data as T;
}
export function saveJSON(data:unknown, name:string) {
  const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
  const a=document.createElement('a');a.href=url;a.download=name;a.click();URL.revokeObjectURL(url);
}
