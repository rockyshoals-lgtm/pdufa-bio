import { cookie } from '../_session.mjs';
export default (req, res) => {
  res.setHeader('Set-Cookie', cookie('pd_session', '', 0));
  res.writeHead(303, { Location: '/' });
  res.end();
};
